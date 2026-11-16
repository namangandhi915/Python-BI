"""Automated Batch 9+10 regression tests (pure computations, not browser tests).

Run from the project root:
    python scripts/run_final_gate_tests.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from scalable_analytics import (
    numeric_measure_options, category_chart_data, histogram_chart_data,
    is_ratio_measure, scatter_chart_data, time_chart_data,
)
from performance_lab import benchmark_grouping, MAX_BENCHMARK_ROWS


def close(actual, expected):
    assert math.isclose(float(actual), float(expected), abs_tol=1e-9), (actual, expected)


def fails(function, message=""):
    try:
        function()
    except ValueError:
        return
    raise AssertionError("Expected a validation error: " + message)


def test_chart_math():
    # Deliberately inconsistent and duplicate row indices test positional alignment.
    source = pd.DataFrame({
        "Product": ["A", "B", "A", None, "C", "B"],
        "Date": ["2026-01-02", "2026-01-05", "2026-02-08", "BAD", "2026-02-09", "2026-04-01"],
        "Sales": [100, 200, 300, 400, 500, np.nan],
        "Profit Margin (%)": [10, 11, 12, 13, 14, 15],
    }, index=[7, 7, 1, 2, 2, 9])
    calc = pd.DataFrame({
        "Net Revenue": [90, 185, 290, 385, 480, 590],
        "Profit After Mapped Costs": [30, 50, -5, 25, 200, 110],
    }, index=[300, 300, 301, 8, 9, 10])
    before = source.copy(deep=True)
    before_calc = calc.copy(deep=True)
    options = numeric_measure_options(source, calc)
    assert "Source: Sales" in options and "Calculated: Net Revenue" in options
    assert is_ratio_measure("Source: Profit Margin (%)")

    result, meta = category_chart_data(source, calc, "Product", "Calculated: Net Revenue", top_n=2)
    close(result["Value"].iloc[0], 775)
    return source, calc, before, before_calc


def test_category_correctness(source, calc):
    result, meta = category_chart_data(source, calc, "Product", "Calculated: Net Revenue", top_n=2)
    assert list(result["Category"]) == ["B", "C"]
    close(result.iloc[0]["Value"], 775)
    close(result.iloc[1]["Value"], 480)
    assert meta["all_groups"] == 4 and meta["truncated_groups"] == 2
    close(meta["complete_metric_total"], 2020)

    full, _ = category_chart_data(source, calc, "Product", "Calculated: Net Revenue", top_n=50)
    close(full["Value"].sum(), 2020)
    donut, donut_meta = category_chart_data(
        source, calc, "Product", "Calculated: Net Revenue", top_n=2, with_remainder=True
    )
    assert len(donut) == 3 and donut_meta["truncated_groups"] == 2
    close(donut["Value"].sum(), 2020)
    assert "Other categories" in donut.iloc[-1]["Category"]
    missing = full.loc[full["Category"] == "(Missing)"]
    close(missing["Value"].iloc[0], 385)

    lowest, _ = category_chart_data(source, calc, "Product", "Calculated: Net Revenue",
                                    top_n=2, direction="Lowest")
    assert lowest.iloc[0]["Category"] == "A"  # A=380, missing=385, C=480, B=775
    fails(lambda: category_chart_data(source, calc, "Product", "Source: Profit Margin (%)", aggregation="Sum"),
          "ratio sum")
    negative_finance = calc.copy()
    negative_finance.iloc[4, negative_finance.columns.get_loc("Profit After Mapped Costs")] = -200
    fails(lambda: category_chart_data(source, negative_finance, "Product",
                                      "Calculated: Profit After Mapped Costs", with_remainder=True), "negative donut")
    fails(lambda: category_chart_data(source, calc, "Product", "Calculated: Net Revenue", top_n=51),
          "top n limit")
    fails(lambda: category_chart_data(source.iloc[:-1], calc, "Product", "Calculated: Net Revenue"),
          "frame alignment")
    # Missing numeric values are explicitly excluded rather than treated as zero.
    sales, info = category_chart_data(source, calc, "Product", "Source: Sales", top_n=50)
    assert info["excluded_measure_rows"] == 1
    close(sales["Value"].sum(), 1500)


def test_time_correctness(source, calc):
    times, info = time_chart_data(source, calc, "Date", "Calculated: Net Revenue", "Monthly")
    assert times["Period"].tolist() == ["2026-01", "2026-02", "2026-04"]
    close(times.loc[times["Period"] == "2026-01", "Value"].iloc[0], 275)
    close(times.loc[times["Period"] == "2026-02", "Value"].iloc[0], 770)
    assert info["excluded_invalid_dates"] == 1 and info["included_rows"] == 5
    avg, _ = time_chart_data(source, calc, "Date", "Calculated: Net Revenue", "Monthly", "Average")
    close(avg.loc[avg["Period"] == "2026-01", "Value"].iloc[0], 137.5)
    fails(lambda: time_chart_data(source, calc, "Date", "Source: Profit Margin (%)", aggregation="Sum"),
          "sum ratio")
    fails(lambda: time_chart_data(source, calc, "Date", "Calculated: Net Revenue", cadence="Daily"),
          "unsupported cadence")


def test_scatter_histogram(source, calc):
    points, meta = scatter_chart_data(source, calc, "Source: Sales", "Calculated: Net Revenue", 2)
    assert len(points) == 2 and meta["valid_rows"] == 5 and meta["excluded_rows"] == 1
    points_again, _ = scatter_chart_data(source, calc, "Source: Sales", "Calculated: Net Revenue", 2)
    pd.testing.assert_frame_equal(points, points_again)
    fails(lambda: scatter_chart_data(source, calc, "Source: Sales", "Calculated: Net Revenue", 1_000_001),
          "too many points")
    hist, meta = histogram_chart_data(source, calc, "Source: Sales", bins=20)
    assert int(hist["Records"].sum()) == 5 and meta["excluded_measure_rows"] == 1
    fails(lambda: histogram_chart_data(source, calc, "Source: Sales", bins=200), "bins limit")


def test_bounded_benchmark():
    n = 100_000
    source = pd.DataFrame({
        "Category": np.where(np.arange(n) % 2 == 0, "Alpha", "Beta"),
        "Value": np.arange(n, dtype=float),
        "Extra": ["Supplementary data"] * n,
    })
    orig = source.head(5).copy(deep=True)
    result, summary = benchmark_grouping(source, "Category", "Value", MAX_BENCHMARK_ROWS)
    assert result["source_rows"] == n and result["sample_rows"] == MAX_BENCHMARK_ROWS
    assert result["group_count"] == 2 and not result["full_source_benchmarked"]
    assert int(summary["Records"].sum()) == MAX_BENCHMARK_ROWS
    assert result["elapsed_ms"] >= 0
    pd.testing.assert_frame_equal(source.head(5), orig)
    fails(lambda: benchmark_grouping(source, "Category", "Value", 100_000), "benchmark bound")
    fails(lambda: benchmark_grouping(source, "Category", "Category", 200), "numeric validation")


def test_practice_workbook():
    paths = [
        Path(__file__).resolve().parents[1] / "data" / "business" / "Python_BI_Complete_Business_Dataset.xlsx",
        Path(__file__).resolve().parents[1] / "data" / "business" / "Python_BI_Complete_Business_Dataset.xlsx",
    ]
    found = next((p for p in paths if p.is_file()), None)
    if found is None:
        print("NOTE: Practice workbook not found in project; synthetic tests cover chart calculations.")
        return
    df = pd.read_excel(found, sheet_name="Business Data")
    from commerce_engine import calculate_commercial_metrics
    # Real local install includes Streamlit for commerce_engine. Test module import at runtime.
    calc, totals = calculate_commercial_metrics(df, "Sales", "Total Cost")
    by_product, audit = category_chart_data(df, calc, "Product", "Calculated: Net Revenue", top_n=50)
    close(by_product["Value"].sum(), totals["net_revenue"])
    trend, meta = time_chart_data(df, calc, "Date", "Calculated: Net Revenue", "Monthly")
    assert len(trend) == 1 and meta["included_rows"] == len(df)
    close(trend["Value"].sum(), totals["net_revenue"])
    print("Practice workbook: chart totals reconcile with commercial totals")


if __name__ == "__main__":
    src, finance, orig_src, orig_finance = test_chart_math()
    test_category_correctness(src, finance)
    test_time_correctness(src, finance)
    test_scatter_histogram(src, finance)
    test_bounded_benchmark()
    pd.testing.assert_frame_equal(src, orig_src)
    pd.testing.assert_frame_equal(finance, orig_finance)
    test_practice_workbook()
    print("PASS: Chart aggregation, bounded samples, date exclusions, ratio safeguards, finance reconciliation, source immutability")
