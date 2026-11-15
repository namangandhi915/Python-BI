"""Run with: python scripts/run_final_gate_tests.py (no Streamlit required)."""
from __future__ import annotations

import io
from pathlib import Path
import pandas as pd

from audit_exports import build_financial_export, excel_safe_csv
from performance_insights import category_profitability, loss_making_rows, price_sensitivity
from business_metrics import break_even_scenario


def assert_close(actual, target, message):
    assert abs(float(actual) - float(target)) < 1e-7, message


def test_export_headers_and_source_preserved():
    data = pd.DataFrame({
        "Product": ["A", "B", "C"],
        "Customer": ["=2+2", "@SUM(A1:A2)", "normal"],
        "BI_Net_Revenue": [999, 999, 999],
        "Sales": [120, 30, 40],
    }, index=[10, 10, 99])
    calculations = pd.DataFrame({
        "Gross Revenue": [120, 30, 40],
        "Net Revenue": [120, 30, 40],
        "Mapped Costs": [70, 50, 25],
        "Profit After Mapped Costs": [50, -20, 15],
        "Loss After Mapped Costs": [0, 20, 0],
    })
    original = data.copy(deep=True)
    result = build_financial_export(data, calculations)
    assert len(result) == 3
    assert result.columns.is_unique
    assert "BI_Gross_Revenue" in result
    assert "BI_Net_Revenue_2" in result, "Must not overwrite a real source field"
    assert "BI_Profit_After_Mapped_Costs" in result
    assert result.iloc[1]["BI_Profit_After_Mapped_Costs"] == -20
    csv = excel_safe_csv(result)
    assert csv.startswith(b"\xef\xbb\xbf"), "Excel UTF-8 BOM missing"
    loaded = pd.read_csv(io.BytesIO(csv), encoding="utf-8-sig")
    assert loaded.loc[0, "Customer"] == "'=2+2"
    assert loaded.loc[1, "Customer"] == "'@SUM(A1:A2)"
    assert loaded.loc[2, "Customer"] == "normal"
    assert_close(loaded["BI_Profit_After_Mapped_Costs"].sum(), 45, "Profit changed in export")
    pd.testing.assert_frame_equal(data, original)
    try:
        build_financial_export(data, calculations.head(2))
        assert False, "Mismatched source/calculated rows were allowed"
    except ValueError:
        pass
    return data, calculations


def test_category_and_exceptions(data, calculations):
    grouping = category_profitability(data, calculations, "Product")
    assert grouping["Records"].sum() == len(data)
    assert_close(grouping["Net Revenue"].sum(), calculations["Net Revenue"].sum(), "Revenue reconciliation")
    assert_close(grouping["Mapped Costs"].sum(), calculations["Mapped Costs"].sum(), "Cost reconciliation")
    assert_close(grouping["Profit After Mapped Costs"].sum(), calculations["Profit After Mapped Costs"].sum(), "Profit reconciliation")
    exceptions = loss_making_rows(data, calculations)
    assert len(exceptions) == 1
    assert exceptions.iloc[0]["Product"] == "B"
    # Null categories must be visible and zero-revenue margin undefined.
    data_null = pd.DataFrame({"Category": [None, "D"]})
    calc = pd.DataFrame({"Net Revenue": [0, 10], "Mapped Costs": [5, 3], "Profit After Mapped Costs": [-5, 7]})
    null_summary = category_profitability(data_null, calc, "Category")
    missing = null_summary.loc[null_summary["Category"] == "(Missing)"].iloc[0]
    assert pd.isna(missing["Profit Margin %"])
    assert missing["Records"] == 1
    return True


def test_sensitivity():
    report = price_sensitivity(1000, 20, 8)
    assert report["Price Change %"].tolist() == [-10, -5, 0, 5, 10]
    for row in report.itertuples(index=False):
        expected = break_even_scenario(1000, row[1], 8)
        assert row[3] == expected["break_even_units"]
    assert report.loc[report["Price Change %"] == 0, "Break-even Units"].iloc[0] == 84
    assert pd.isna(price_sensitivity(1000, 10, 11).iloc[2]["Break-even Units"])
    assert price_sensitivity(0, 10, 3).loc[2, "Break-even Units"] == 0
    try:
        price_sensitivity(100, 1, 0, percent_changes=(-150,))
        assert False, "Negative price scenario was allowed"
    except ValueError:
        pass


def test_sample_workbook():
    path = Path(__file__).resolve().parents[1] / "data" / "business" / "Python_BI_Complete_Business_Dataset.xlsx"
    # In the test workspace, a user may have the dataset in a different path.
    if not path.exists():
        return "Sample-workbook integration skipped (project Data workbook not found)."
    source = pd.read_excel(path, sheet_name="Business Data")
    from commerce_engine import calculate_commercial_metrics
    calc, totals = calculate_commercial_metrics(source, "Sales", "Total Cost")
    output = build_financial_export(source, calc)
    summary = category_profitability(source, calc, "Product")
    assert_close(summary["Net Revenue"].sum(), totals["net_revenue"], "Workbook grouped revenue mismatch")
    assert_close(summary["Profit After Mapped Costs"].sum(), totals["profit_after_mapped_costs"], "Workbook grouped profit mismatch")
    assert len(output) == len(source)
    assert len(loss_making_rows(source, calc)) == int(calc["Profit After Mapped Costs"].lt(0).sum())
    return f"Sample-workbook integration validated: {len(source)} rows."


if __name__ == "__main__":
    data, calculated = test_export_headers_and_source_preserved()
    test_category_and_exceptions(data, calculated)
    test_sensitivity()
    print(test_sample_workbook())
    print("PASS: Safe BI_ exports, collision handling, profitability reconciliation, loss exceptions, break-even sensitivity")
