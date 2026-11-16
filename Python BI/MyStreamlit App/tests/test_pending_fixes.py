"""Regression coverage for revenue mapping and period-end market analysis."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
from investment_engine import evaluate_market_history
from commerce_engine import calculate_commercial_metrics
from report_engine import build_executive_report


def test_period_end_prices_and_incomplete_periods():
    data = pd.DataFrame({"date": pd.to_datetime(["2023-12-29", "2024-01-01", "2024-03-28", "2024-04-03", "2024-12-30", "2025-01-10"]),
                         "price": [10., 11., 13., 14., 18., 20.]})
    summary, quarterly = evaluate_market_history(data, "date", "price", "Quarterly", aggregate_periods=True)
    assert quarterly["Price"].tolist() == [10., 13., 14., 18., 20.]
    assert summary["observed_return_count"] == 4
    _, yearly = evaluate_market_history(data, "date", "price", "Yearly", aggregate_periods=True)
    assert yearly["Price"].tolist() == [10., 18., 20.]
    assert yearly["Date"].iloc[-1].day == 10


def test_period_aggregation_rejects_bad_source_and_too_few_periods():
    source = pd.DataFrame({"date": ["2024-01-01", "2024-02-01"], "price": [10., 20.]})
    try:
        evaluate_market_history(source, "date", "price", "Yearly", aggregate_periods=True)
        raise AssertionError("A single year must be rejected")
    except ValueError as exc:
        assert "two distinct dated price periods" in str(exc)
    source.loc[0, "price"] = np.inf
    try:
        evaluate_market_history(source, "date", "price", "Quarterly", aggregate_periods=True)
        raise AssertionError("Invalid prices must be rejected")
    except ValueError as exc:
        assert "Invalid rows" in str(exc)


def test_net_revenue_does_not_become_gross_or_auto_select_year():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.session_state["uploaded_df"] = pd.DataFrame({"year": [2024, 2025], "net_revenue_usd": [100., 150.]})
    app.session_state["uploaded_name"] = "net example"
    app.run()
    app.sidebar.radio[0].set_value("Data Workspace").run()
    app.radio(key="workspace_mode").set_value("Commercial Intelligence").run()
    assert not app.exception
    assert app.selectbox(key="ci_revenue").value == "— Not provided —"
    assert any("Select a revenue field" in item.value for item in app.info)
    app.selectbox(key="ci_revenue").select("net_revenue_usd").run()
    assert not app.exception
    assert any(metric.label == "Gross Revenue" and metric.value == "Not provided" for metric in app.metric)
    assert any(metric.label == "Net Revenue" and metric.value == "250.00" for metric in app.metric)
    assert app.session_state["commercial_mapping"]["basis"] == "net"
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert not app.exception
    assert any(metric.label == "Gross Revenue" and metric.value == "Not provided" for metric in app.metric)
    assert any(metric.label == "Net Revenue" and metric.value == "250.00" for metric in app.metric)


def test_net_report_and_duplicate_deduction_guard():
    data = pd.DataFrame({"net": [100., 150.], "discount": [10., 5.]})
    calculations, totals = calculate_commercial_metrics(data, "net", revenue_basis="net")
    assert "Gross Revenue" not in calculations and "gross_revenue" not in totals
    try:
        calculate_commercial_metrics(data, "net", discount="discount", revenue_basis="net")
        raise AssertionError("Discount must not be deducted twice")
    except ValueError as exc:
        assert "again" in str(exc)
    report = build_executive_report(data, calculations, totals, dataset_name="Net", category=None,
                                    date_column=None, period="Monthly", field_mapping={"Net revenue": "net"},
                                    filter_notes="All rows")
    assert "Not provided" in report["html"].decode("utf-8")
    assert totals["net_revenue"] == 250


def test_forecast_fragment_with_20000_prices():
    app = AppTest.from_string(f'''
import sys
sys.path.insert(0, {str(ROOT / "modules")!r})
import pandas as pd
import numpy as np
from forecast_panel import render_market_research
history = pd.DataFrame({{"Date": pd.date_range("1950-01-01", periods=20000, freq="D"),
                         "Price": 100 * np.exp(np.arange(20000) * 0.00001)}})
render_market_research(history, "Daily", True)
''', default_timeout=60).run()
    assert not app.exception
    app.button(key="ii_mc_run").click().run()
    assert not app.exception
    assert any("Historical out-of-sample backtest" in item.value for item in app.markdown)


if __name__ == "__main__":
    test_period_end_prices_and_incomplete_periods()
    test_period_aggregation_rejects_bad_source_and_too_few_periods()
    test_net_revenue_does_not_become_gross_or_auto_select_year()
    test_net_report_and_duplicate_deduction_guard()
    test_forecast_fragment_with_20000_prices()
    print("PASS: period-end aggregation and safe revenue mapping")
