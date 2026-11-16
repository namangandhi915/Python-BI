"""Regression checks for the updated workspace, using in-memory synthetic data only.

Streamlit AppTest requires local loopback sockets on Windows. No library files are written.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from io import BytesIO
import json
import sys
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
from investment_engine import evaluate_market_history
from commerce_engine import mapping_scope, calculate_commercial_metrics
from assurance_contracts import inspect_dataset
from dataset_library import save_active_dataset


def check_app(app, step):
    assert not app.exception, (step, [e.message for e in app.exception])
    assert not app.error, (step, [e.value for e in app.error])


class Upload(BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.name = name
        self.size = len(content)


def main():
    with TemporaryDirectory() as folder:
        storage = Path(folder) / "library"
        first = Upload("first.csv", b"x,y\n1,2\n")
        second = Upload("second.csv", b"x,y\n3,4\n")
        save_active_dataset(first, storage)
        first_metadata = json.loads((storage / "active_dataset.json").read_text())
        save_active_dataset(second, storage)
        second_metadata = json.loads((storage / "active_dataset.json").read_text())
        assert first_metadata["stored_name"] != second_metadata["stored_name"]
        assert len(list(storage.glob("*.csv"))) == 2
        save_active_dataset(first, storage)
        assert len(list(storage.glob("*.csv"))) == 2
        assert json.loads((storage / "active_dataset.json").read_text())["stored_name"] == first_metadata["stored_name"]

    frame = pd.DataFrame({"Date": ["2024-01-01", "2024-02-01"], "Sales": [10., 20.], "Total Cost": [5., 10.], "Product": [" A ", "B"], "Check": ["1", "inf"]})
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.session_state["uploaded_df"] = frame
    app.session_state["uploaded_name"] = "Synthetic A"
    app.run(); check_app(app, "home")
    app.sidebar.radio[0].set_value("Data Workspace").run(); check_app(app, "explore")
    app.radio(key="workspace_mode").set_value("Prepare & Validate").run(); check_app(app, "prepare")
    app.selectbox(key="explorer_preview_widget").select(1_000_000).run()
    app.selectbox(key="prep_numeric_check").select("Check").run(); check_app(app, "numeric validation")
    assert any(m.label == "Invalid Numeric Values" and m.value == "1" for m in app.metric)
    app.radio(key="workspace_mode").set_value("Explore").run(); check_app(app, "preview persistence")
    assert app.session_state["explorer_preview_setting"] == 1_000_000
    app.session_state["explorer_datasets"] = {"a": ("A.csv", frame), "b": ("B.csv", frame.iloc[:1].copy())}
    app.run(); check_app(app, "multiple files")
    assert len(app.session_state["uploaded_df"]) == 3
    app.multiselect(key="explorer_selected_files").set_value(["b"]).run(); check_app(app, "one file selected")
    assert len(app.session_state["uploaded_df"]) == 1
    app.radio(key="workspace_mode").set_value("Prepare & Validate").run(); check_app(app, "leave selection")
    app.radio(key="workspace_mode").set_value("Explore").run(); check_app(app, "restore selection")
    assert len(app.session_state["uploaded_df"]) == 1
    app.multiselect(key="explorer_selected_files").set_value(["a", "b"]).run(); check_app(app, "files reselected")
    assert len(app.session_state["uploaded_df"]) == 3
    app.radio(key="workspace_mode").set_value("Commercial Intelligence").run(); check_app(app, "commercial")
    scope = app.session_state["commercial_mapping"]["scope"]
    assert scope == mapping_scope(app.session_state["uploaded_df"], app.session_state["active_data_token"])
    app.sidebar.radio[0].set_value("Dashboard").run(); check_app(app, "dashboard")
    assert any("selected mapping" in c.value for c in app.caption)
    app.session_state["uploaded_name"] = "Different dataset"
    app.session_state["active_data_token"] = "different-dataset"
    app.run(); check_app(app, "different dataset mapping")
    assert any("Suggested financial fields" in c.value for c in app.caption)
    app.sidebar.radio[0].set_value("Investment Intelligence").run(); check_app(app, "investment")

    for frequency, offset in (("Quarterly", "QS"), ("Yearly", "YS")):
        market = pd.DataFrame({"date": pd.date_range("1980-01-01", periods=40, freq=offset), "price": np.arange(100., 140.)})
        summary, _ = evaluate_market_history(market, "date", "price", frequency)
        assert summary["frequency_consistent"] and summary["observed_return_count"] == 39

    million = pd.DataFrame({"x": np.arange(1_000_000)})
    summary, _ = inspect_dataset(million, sample_size=1_000_000)
    assert summary["sample_rows"] == 1_000_000
    assert mapping_scope(frame, "A") != mapping_scope(frame, "B")
    values, totals = calculate_commercial_metrics(frame, "Sales", "Total Cost")
    assert totals["net_revenue"] == 30 and len(values) == 2
    print("PASS: Real Streamlit navigation, selection, preview, numeric validation, mapping isolation, frequencies, and million-row quality limit")

if __name__ == "__main__":
    main()
