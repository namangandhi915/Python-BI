"""Regression tests for financial period comparison and sampled profiling.

Run: python scripts/run_final_gate_tests.py
Pure computations only; final Streamlit UI check must be done in the browser.
"""
from __future__ import annotations
import math
import pandas as pd
from period_comparison import available_periods, compare_periods
from data_readiness import dataset_profile


def close(actual, expected):
    assert math.isclose(float(actual), float(expected), abs_tol=1e-8), (actual, expected)


def test_period_comparison():
    source = pd.DataFrame({
        "Date": ["2026-01-05", "2026-01-14", "2026-02-03", "2026-02-28", "bad", "2026-04-01"],
        "Product": ["A", "B", "A", None, "A", "C"],
        "Sales": [100, 50, 125, 45, 100, 90],
    }, index=[0, 0, 1, 2, 3, 4])
    finance = pd.DataFrame({
        "Gross Revenue": [100, 50, 125, 45, 100, 90],
        "Net Revenue": [100, 50, 125, 45, 100, 90],
        "Mapped Costs": [40, 20, 65, 25, 40, 30],
        "Profit After Mapped Costs": [60, 30, 60, 20, 60, 60],
    }, index=[12, 12, 14, 15, 16, 17])
    original = source.copy(deep=True)
    periods, excluded = available_periods(source, "Date", "Monthly")
    assert periods == ["2026-01", "2026-02", "2026-04"], periods
    assert excluded == 1
    totals, groups, audit = compare_periods(source, finance, "Date", "Monthly", "2026-01", "2026-02", "Product")
    assert audit["periods_are_adjacent"] and audit["earlier_rows"] == 2 and audit["later_rows"] == 2
    assert audit["excluded_invalid_dates"] == 1
    assert audit["excluded_other_period_rows"] == 1
    net = totals[totals["Metric"] == "Net Revenue"].iloc[0]
    close(net["Earlier"], 150)
    close(net["Later"], 170)
    close(net["Change %"], 20 / 150 * 100)
    close(groups["Earlier Revenue"].sum(), 150)
    close(groups["Later Revenue"].sum(), 170)
    close(groups["Earlier Profit"].sum(), 90)
    close(groups["Later Profit"].sum(), 80)
    assert "(Missing)" in groups["Category"].tolist()
    _, _, nonadjacent = compare_periods(source, finance, "Date", "Monthly", "2026-01", "2026-04")
    assert not nonadjacent["periods_are_adjacent"]
    pd.testing.assert_frame_equal(source, original)
    try:
        compare_periods(source, finance, "Date", "Monthly", "2026-02", "2026-01")
        raise AssertionError("Reverse ordering passed")
    except ValueError:
        pass
    try:
        compare_periods(source, finance.head(2), "Date", "Monthly", "2026-01", "2026-02")
        raise AssertionError("Row-count mismatch passed")
    except ValueError:
        pass
    finance_negative = finance.copy()
    finance_negative.loc[finance_negative.index[0], "Net Revenue"] = -50
    # Entire January prior period becomes nonpositive, so growth is undefined.
    finance_negative.iloc[1, finance_negative.columns.get_loc("Net Revenue")] = -60
    results, _, _ = compare_periods(source, finance_negative, "Date", "Monthly", "2026-01", "2026-02")
    assert pd.isna(results.loc[results.Metric == "Net Revenue", "Change %"].iloc[0])
    return source


def test_profile():
    frame = pd.DataFrame({"A": [1, None, 1, 1], "B": ["x", "y", "x", "x"]}, index=[1, 3, 1, 5])
    original = frame.copy(deep=True)
    values, fields, preview = dataset_profile(frame, sample_limit=10, exact_missing_scan=True)
    assert values["source_rows"] == 4 and values["sample_rows"] == 4
    assert values["exact_missing_cells"] == 1
    assert int(fields.loc[fields.Column == "A", "Exact missing in source"].iloc[0]) == 1
    assert values["sample_duplicate_rows"] == 2
    assert len(preview) == 4
    pd.testing.assert_frame_equal(frame, original)
    small, fields, preview = dataset_profile(frame, sample_limit=2, exact_missing_scan=False)
    assert small["sample_rows"] == 2 and small["exact_missing_cells"] is None
    assert "Exact missing in source" not in fields.columns
    empty, columns, preview = dataset_profile(frame.head(0), sample_limit=50)
    assert empty["sample_rows"] == 0 and empty["source_rows"] == 0
    big = pd.DataFrame({"K": range(55_000), "Date": ["2026-02-01"] * 55_000})
    summary, cols, sample = dataset_profile(big, sample_limit=3_000)
    assert summary["source_rows"] == 55_000 and summary["sample_rows"] == 3_000
    assert len(sample) == 3_000
    return True


if __name__ == "__main__":
    test_period_comparison()
    test_profile()
    print("PASS: Period comparison reconciliation, invalid dates, negative-baseline guard, sampled profiling, source immutability")
