"""Dashboard source tools must remain usable without valid financial mapping."""
from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def open_dashboard(frame):
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.session_state["uploaded_df"] = frame
    app.session_state["uploaded_name"] = "Dashboard regression"
    app.run()
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert not app.exception
    return app


def assert_sections(app):
    labels = [item.label for item in app.expander]
    for title in ("02  ·  Category profitability", "03  ·  Compare financial", "04  ·  Column comparison", "05  ·  Interactive chart studio", "06  ·  Executive report", "07  ·  Revenue concentration"):
        assert any(title in label for label in labels), (title, labels)


def main():
    frame = pd.DataFrame({"region": ["East", "West"], "units": [3, 5]})
    app = open_dashboard(frame)
    assert_sections(app)
    app.checkbox(key="studio_run").check().run()
    assert not app.exception
    assert "Source: units" in app.selectbox(key="studio_metric").options
    app.selectbox(key="studio_chart_type").select("Scatter").run()
    assert not app.exception
    assert app.selectbox(key="studio_scatter_y").value == "Source: units"

    mapped = open_dashboard(pd.DataFrame({"Sales": [10., 20.], "region": ["East", "West"]}))
    assert not mapped.error
    assert_sections(mapped)

    invalid = open_dashboard(pd.DataFrame({"Sales": [10., float("nan")], "region": ["East", "West"]}))
    assert any("Financial calculation blocked" in item.value for item in invalid.error)
    assert_sections(invalid)
    invalid.checkbox(key="studio_run").check().run()
    assert not invalid.exception
    assert "Source: Sales" in invalid.selectbox(key="studio_metric").options

    nonnumeric = open_dashboard(pd.DataFrame({"name": ["A", "B"], "region": ["East", "West"]}))
    assert_sections(nonnumeric)
    nonnumeric.checkbox(key="studio_run").check().run()
    assert not nonnumeric.exception
    assert any("No numeric fields are available to chart" in item.value for item in nonnumeric.info)
    print("PASS: dashboard sections and source charts remain available without valid financial mapping")


if __name__ == "__main__":
    main()
