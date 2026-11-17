"""Independent tools remain available when other inputs are missing or invalid."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
from business_metrics import revenue_by_period


def main():
    with TemporaryDirectory() as storage:
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        source = source.replace('STORAGE_DIR = Path(__file__).resolve().parent / "stored_datasets"',
                                f'STORAGE_DIR = Path({storage!r})')
        source = f'import sys\nsys.path.insert(0, {str(ROOT / "modules")!r})\n' + source
        app = AppTest.from_string(source, default_timeout=60).run()
        app.sidebar.radio[0].set_value("Data Workspace").run()
        app.radio(key="workspace_mode").set_value("Commercial Intelligence").run()
        app.radio(key="commercial_view").set_value("Business Planning").run()
        assert not app.exception
        assert app.number_input(key="plan_fixed") is not None
        app.number_input(key="plan_fixed").set_value(1000.0).run()
        app.number_input(key="plan_price").set_value(40.0).run()
        app.number_input(key="plan_variable").set_value(20.0).run()
        assert any(m.label == "Break-even units" and m.value == "50" for m in app.metric)

    dates = ["2024-01-01T00:00:00+00:00", "2024-02-01T00:00:00+05:30"]
    try:
        revenue_by_period(pd.Series(dates), pd.Series([100., 200.]))
        raise AssertionError("Mixed time zones must be rejected clearly")
    except ValueError as error:
        assert "time zone" in str(error)

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.session_state["uploaded_df"] = pd.DataFrame({"Date": dates, "Sales": [100., 200.]})
    app.session_state["uploaded_name"] = "Mixed dates"
    app.run()
    app.sidebar.radio[0].set_value("Data Workspace").run()
    app.radio(key="workspace_mode").set_value("Commercial Intelligence").run()
    assert not app.exception
    assert any("Revenue trend is unavailable" in w.value for w in app.warning)
    assert any("Audit individual calculations" in e.label for e in app.expander)
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert not app.exception
    assert any("Interactive chart studio" in e.label for e in app.expander)
    app.checkbox(key="ex_use_date_filter").check().run()
    assert not app.exception
    assert any("Date filter unavailable" in w.value for w in app.warning)
    assert any("Interactive chart studio" in e.label for e in app.expander)
    assert not any(m.label == "Net Revenue" for m in app.metric)
    print("PASS: independent planning, mixed-date isolation, and dashboard visibility")


if __name__ == "__main__":
    main()
