"""Regression checks for Batch13 report ZIP + Batch14 category analysis / scaling.
Use: python test_phase3_batch1314.py
"""
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
import types
import zipfile
import math
from datetime import datetime, timezone

import pandas as pd

# Pure calculation checks also work if Streamlit is not installed in test container.
try:
    import streamlit
except ImportError:
    sys.modules["streamlit"] = types.SimpleNamespace()

from commerce_engine import calculate_commercial_metrics
from report_engine import build_executive_report
from report_bundle import build_report_archive, verify_report_archive
from portfolio_analytics import build_category_concentration
from benchmark_phase3 import benchmark


def assert_raises(func):
    try:
        func()
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def sample():
    data = pd.DataFrame({
        "Date": ["2026-01-01", "2026-02-01", None, "2026-02-03"],
        "Product": ["Alpha", "Beta", "Alpha", None],
        "Sales": [200.0, 300.0, 400.0, 100.0],
        "Cost": [80.0, 350.0, 300.0, 20.0],
    }, index=[11, 11, 14, 29])
    calc, totals = calculate_commercial_metrics(data, "Sales", "Cost")
    return data, calc, totals


def test_report_pack():
    data, calc, totals = sample()
    orig = data.copy(deep=True)
    report = build_executive_report(
        data, calc, totals,
        dataset_name="<script>Unsafe</script>", category="Product", date_column="Date", period="Monthly",
        field_mapping={"Gross revenue": "Sales", "Cost of sales": "Cost"},
        filter_notes="All records",
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )
    output = build_report_archive(report, dataset_name="Demo", filter_context="All records",
                                  period="Monthly", category="Product", currency="Not specified")
    verified = verify_report_archive(output)
    assert verified["filtered_row_count"] == 4
    assert verified["includes_transaction_level_data"] is False
    with zipfile.ZipFile(io.BytesIO(output)) as z:
        assert "report.html" in z.namelist()
        assert "financial_summary.csv" in z.namelist()
        assert "category_performance.csv" in z.namelist()
        assert "calendar_revenue.csv" in z.namelist()
        assert "manifest.json" in z.namelist()
        assert "<script>Unsafe</script>" not in z.read("report.html").decode("utf-8")
        assert b"Alpha" in z.read("category_performance.csv")
        assert b"2026-02" in z.read("calendar_revenue.csv")
        # Auditable aggregate CSVs must not contain transaction-level IDs.
        assert b"TransactionID" not in z.read("financial_summary.csv")
    pd.testing.assert_frame_equal(data, orig)
    # Change bytes inside ZIP without updating manifest; verifier must stop.
    with zipfile.ZipFile(io.BytesIO(output)) as z:
        members = {name: z.read(name) for name in z.namelist()}
    members["financial_summary.csv"] = b"Tampered data\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, value in members.items():
            z.writestr(name, value)
    assert_raises(lambda: verify_report_archive(buf.getvalue()))
    assert_raises(lambda: build_report_archive({"html": b"Not HTML", "summary": pd.DataFrame(),
                                              "categories": pd.DataFrame(), "periods": pd.DataFrame(),
                                              "matching_rows": 1}, dataset_name="X", filter_context="Y",
                                             period="Monthly", category=None, currency="INR"))


def test_portfolio():
    data, calc, totals = sample()
    original = data.copy(deep=True)
    result = build_category_concentration(data, calc, totals, "Product")
    groups, met = result["groups"], result["metrics"]
    assert groups["Category"].tolist() == ["Alpha", "Beta", "(Missing)"]
    assert math.isclose(float(groups["Net Revenue"].sum()), 1000)
    assert math.isclose(float(groups["Mapped Costs"].sum()), 750)
    assert math.isclose(float(groups["Profit After Mapped Costs"].sum()), 250)
    assert met["category_count"] == 3
    assert math.isclose(met["top_category_share_pct"], 60)
    assert math.isclose(met["top_three_share_pct"], 100)
    assert met["categories_to_80_pct"] == 2
    assert math.isclose(met["concentration_index"], 4600)
    pd.testing.assert_frame_equal(data, original)
    assert_raises(lambda: build_category_concentration(data.iloc[:2], calc, totals, "Product"))
    assert_raises(lambda: build_category_concentration(data, calc, dict(totals, net_revenue=1), "Product"))
    assert_raises(lambda: build_category_concentration(data, calc, totals, "Missing Column"))
    neg = pd.DataFrame({"Product": ["A", "B"], "Sales": [400., -100.]})
    neg_calc, neg_total = calculate_commercial_metrics(neg, "Sales")
    result = build_category_concentration(neg, neg_calc, neg_total, "Product")
    assert result["metrics"]["concentration_available"] is False
    assert "Revenue Share %" not in result["groups"]


def test_benchmark():
    res = benchmark(1000)
    assert res["rows"] == 1000
    assert res["reconciled"] is True
    assert 0 < res["selected_rows"] <= 1000
    assert res["dataframe_memory_mib"] > 0
    assert_raises(lambda: benchmark(999))
    assert_raises(lambda: benchmark(500001))



def test_mocked_category_panel():
    import portfolio_panel
    class Context:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def metric(self, *_, **__): pass
    class Fake:
        def __init__(self):
            self.downloaded = []
            self.charts = 0
        def expander(self, *_, **__): return Context()
        def caption(self, *_, **__): pass
        def selectbox(self, label, options, index=0, **_): return options[index]
        def checkbox(self, *_, **__): return True
        def columns(self, n): return [Context() for _ in range(n)]
        def metric(self, *_, **__): pass
        def plotly_chart(self, *_, **__): self.charts += 1
        def dataframe(self, *_, **__): pass
        def download_button(self, *args, **kwargs): self.downloaded.append((args,kwargs))
        def warning(self, message): raise AssertionError(f"Unexpected warning: {message}")
        def info(self, message): raise AssertionError(f"Unexpected info: {message}")
    src, calc, totals = sample()
    old = portfolio_panel.st
    fake = Fake()
    portfolio_panel.st = fake
    try:
        portfolio_panel.render_portfolio_panel(src, calc, totals)
    finally:
        portfolio_panel.st = old
    assert fake.charts == 1
    assert len(fake.downloaded) == 1
    assert fake.downloaded[0][1]["file_name"] == "python_bi_category_mix.csv"


def test_workbook():
    workbook = Path(__file__).parent / "Data" / "Python_BI_Complete_Business_Dataset.xlsx"
    if not workbook.exists():
        print("Practice workbook not found; synthetic checks still ran")
        return
    data = pd.read_excel(workbook, sheet_name="Business Data")
    calc, totals = calculate_commercial_metrics(data, "Sales", "Total Cost")
    result = build_category_concentration(data, calc, totals, "Product")
    assert math.isclose(float(result["groups"]["Net Revenue"].sum()), 293300)
    assert math.isclose(float(result["groups"]["Profit After Mapped Costs"].sum()), 61500)
    assert result["metrics"]["category_count"] == 5
    assert math.isclose(float(result["groups"]["Revenue Share %"].sum()), 100, abs_tol=.005)
    print("Practice workbook reconciled: revenue 293,300 / mapped-cost profit 61,500")


if __name__ == "__main__":
    test_report_pack()
    test_portfolio()
    test_benchmark()
    test_workbook()
    test_mocked_category_panel()
    print("PASS: Aggregate report ZIP integrity, tamper detection, category shares, reconciliation, bounded synthetic benchmark")
