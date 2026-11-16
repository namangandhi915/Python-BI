"""Pure tests for Batch 11 (audited report) and Batch 12 (Home integration).
Run: python scripts/run_final_gate_tests.py
Real Streamlit page interaction must also be tested once in the browser.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import sys
import types

import pandas as pd

# This calculation logic can run even where the optional Streamlit UI is not installed.
try:
    import streamlit  # noqa: F401
except ImportError:
    sys.modules["streamlit"] = types.SimpleNamespace()

from commerce_engine import calculate_commercial_metrics
from report_engine import build_executive_report


def failed(function):
    try:
        function()
    except ValueError:
        return
    raise AssertionError("Expected a ValueError")


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=.01), (a, b)


def test_from_sample_workbook():
    workbook = Path(__file__).resolve().parents[1] / "data" / "business" / "Python_BI_Complete_Business_Dataset.xlsx"
    if not workbook.exists():
        print("Bundled workbook not present; pure tests continue.")
        return
    source = pd.read_excel(workbook, sheet_name="Business Data")
    original = source.copy(deep=True)
    calc, totals = calculate_commercial_metrics(source, "Sales", "Total Cost")
    bundle = build_executive_report(
        source, calc, totals,
        dataset_name="Python BI Business Transactions 2026", category="Product",
        date_column="Date", period="Monthly",
        field_mapping={"Gross revenue": "Sales", "Cost of sales": "Total Cost"},
        filter_notes="All source records", currency_label="Unspecified",
        generated_at=datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc),
    )
    close(totals["net_revenue"], 293300)
    close(totals["mapped_costs"], 231800)
    close(totals["profit_after_mapped_costs"], 61500)
    assert bundle["matching_rows"] == 20
    assert bundle["missing_date_rows"] == 0
    close(bundle["categories"]["Net Revenue"].sum(), 293300)
    close(bundle["categories"]["Profit After Mapped Costs"].sum(), 61500)
    assert bundle["periods"]["Period"].tolist() == ["2026-01"]
    close(bundle["periods"]["Revenue"].sum(), 293300)
    html = bundle["html"].decode("utf-8")
    assert "Business Performance Report" in html
    assert "01. Financial measures" in html and "04. Field mapping and assumptions" in html
    assert "2026-01" in html and "Save as PDF" in html
    assert "2026-11-07" not in html  # printed date deliberately human-readable, not raw string
    pd.testing.assert_frame_equal(source, original)
    print("Practice workbook: 20 records; revenue/cost/profit/category/time totals reconcile")


def test_malicious_text_and_missing_dates():
    source = pd.DataFrame({
        "Date": ["2026-01-01", "2026-02-01", "BAD"],
        "Product": ["Widget", "<script>alert('x')</script>", None],
        "Sales": [100.0, 210.0, 90.0],
        "Cost": [30.0, 300.0, 20.0],
    }, index=[4, 4, 9])
    before = source.copy(deep=True)
    calc, totals = calculate_commercial_metrics(source, "Sales", "Cost")
    bundle = build_executive_report(
        source, calc, totals,
        dataset_name='<img src=x onerror="alert(1)">', category="Product",
        date_column="Date", period="Monthly",
        field_mapping={"Gross revenue": "Sales", "Injected key": "<b>unsafe</b>"},
        filter_notes='City = "<script>"',
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )
    html = bundle["html"].decode("utf-8")
    assert "<script>alert" not in html and "&lt;script&gt;alert" in html
    assert '<img src=x onerror' not in html and '&lt;img src=x onerror' in html
    assert "<b>unsafe</b>" not in html and "&lt;b&gt;unsafe&lt;/b&gt;" in html
    assert "(Missing)" in html
    assert bundle["missing_date_rows"] == 1
    assert bundle["periods"]["Period"].tolist() == ["2026-01", "2026-02"]
    close(bundle["periods"]["Revenue"].sum(), 310)
    close(bundle["categories"]["Net Revenue"].sum(), 400)
    close(bundle["categories"]["Profit After Mapped Costs"].sum(), 50)
    pd.testing.assert_frame_equal(source, before)

    # Bad mapping / report totals / row-count mismatch must stop a report.
    defaults = dict(dataset_name="X", category="Product", date_column="Date", period="Monthly",
                    field_mapping={"Gross revenue":"Sales"}, filter_notes="All")
    failed(lambda: build_executive_report(source, calc.iloc[:2], totals, **defaults))
    failed(lambda: build_executive_report(source, calc, dict(totals, net_revenue=9), **defaults))
    failed(lambda: build_executive_report(source, calc, totals, **dict(defaults, period="Weekly")))
    failed(lambda: build_executive_report(source, calc, totals, **dict(defaults, category="Absent")))
    # Missing expenses: do NOT create pretend profit or margin.
    no_cost_calc, no_cost_totals = calculate_commercial_metrics(source, "Sales")
    no_cost = build_executive_report(source, no_cost_calc, no_cost_totals, **defaults)
    assert "Profit After Mapped Costs" not in no_cost["categories"].columns
    assert no_cost["summary"].loc[
        no_cost["summary"].Metric == "Profit After Mapped Costs", "Value"
    ].isna().all()
    assert "No cost field was mapped" in no_cost["html"].decode("utf-8")


def test_home_code_wiring():
    project = Path(__file__).resolve().parents[1]
    application = (project / "app.py").read_text(encoding="utf-8")
    dashboard = (project / "modules" / "executive_dashboard.py").read_text(encoding="utf-8")
    style = (project / "assets" / "bi_theme.css").read_text(encoding="utf-8")
    assert "from home_experience import render_home" in application
    assert 'if page == "Home":\n    render_home()' in application
    assert "from executive_report import render_executive_report" in dashboard
    assert "render_executive_report(" in dashboard
    assert ".bi-home-hero" in style and ".bi-home-grid" in style
    assert "render_chart_studio(filtered, calculations)" in dashboard
    assert "render_performance_lab(data)" not in dashboard
    assert '"Data Workspace", "Dashboard"' in application
    # Existing Phase 2 persistence and Phase 3 modules are still in the app.
    assert "def restore_active_dataset" in application
    assert "def save_active_dataset" in application


def test_mocked_ui():
    # Dry-run new widgets without starting the full browser server.
    import executive_report
    import home_experience

    class Context:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def metric(self, *_args, **_kwargs):
            pass

    class FakeStreamlit:
        def __init__(self):
            self.session_state = {}
            self.downloads = []
            self.markups = []
            self.captions = []
        def expander(self, *_args, **_kwargs):
            return Context()
        def columns(self, count):
            return [Context() for _ in range(count)]
        def selectbox(self, _label, choices, index=0, **_kwargs):
            return choices[index]
        def text_input(self, _label, value='', **_kwargs):
            return value
        def button(self, *_args, **_kwargs):
            return True
        def caption(self, *args, **_kwargs):
            self.captions.extend(args)
        def info(self, *_args, **_kwargs):
            pass
        def markdown(self, *args, **_kwargs):
            self.markups.extend(args)
        def metric(self, *_args, **_kwargs):
            pass
        def dataframe(self, *_args, **_kwargs):
            pass
        def success(self, *_args, **_kwargs):
            pass
        def warning(self, *args, **_kwargs):
            raise AssertionError(f"Unexpected warning: {args}")
        def error(self, *args, **_kwargs):
            raise AssertionError(f"Unexpected error: {args}")
        def download_button(self, *args, **kwargs):
            assert kwargs.get('on_click') == 'ignore', 'Report download should not rerun Streamlit'
            self.downloads.append((args, kwargs))

    fake = FakeStreamlit()
    former_report = executive_report.st
    former_home = home_experience.st
    executive_report.st = fake
    home_experience.st = fake
    try:
        source = pd.DataFrame({
            'Date': ['2026-01-01', '2026-02-01'],
            'Product': ['A','B'], 'Sales': [150.0, 75.0], 'Cost': [50.0,80.0],
        })
        calc, totals = calculate_commercial_metrics(source,'Sales','Cost')
        executive_report.render_executive_report(source,calc,totals,
                                                 dataset_name='Test', mapping={'Sales':'Sales'},
                                                 filter_summary='All')
        assert len(fake.downloads) == 5, 'Expected ZIP, HTML and three CSV downloads'
        assert any(item[1].get('file_name') == 'python_bi_executive_report_pack.zip'
                   for item in fake.downloads), 'Audit pack download missing'
        assert any(item[1].get('file_name') == 'python_bi_executive_report.html'
                   for item in fake.downloads)
        fake.session_state['uploaded_df'] = source
        fake.session_state['uploaded_name'] = '<Customer & Company>'
        home_experience.render_home()
        assert any('Clarity in every decision' in text for text in fake.markups)
        assert any('&lt;Customer &amp; Company&gt;' in text for text in fake.markups)
    finally:
        executive_report.st = former_report
        home_experience.st = former_home


if __name__ == "__main__":
    test_from_sample_workbook()
    test_malicious_text_and_missing_dates()
    test_home_code_wiring()
    test_mocked_ui()
    print("PASS: Report reconciliations, escaped HTML, missing dates, missing costs, invalid inputs, source immutability, application integration")
