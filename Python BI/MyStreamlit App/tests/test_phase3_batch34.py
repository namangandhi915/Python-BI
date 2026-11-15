"""Run from project root: python scripts/run_final_gate_tests.py (no browser required)."""
from pathlib import Path

import pandas as pd

from business_metrics import apply_dashboard_filters, break_even_scenario, revenue_by_period


base = pd.DataFrame({
    "Date": ["2026-01-02", "2026-01-18", "2026-02-07", "2026-04-09"],
    "Product": ["Laptop", "Phone", "Laptop", "Phone"],
    "Sales": [100.0, 200.0, 150.0, 300.0],
    "Total Cost": [60.0, 100.0, 75.0, 120.0],
})
source = base.copy(deep=True)
filtered = apply_dashboard_filters(base, category_column="Product", categories=["Laptop"])
assert len(filtered) == 2
assert filtered["Sales"].sum() == 250
filtered2 = apply_dashboard_filters(
    base, category_column="Product", categories=["Laptop"],
    date_column="Date", start_date=pd.Timestamp("2026-02-01").date(),
    end_date=pd.Timestamp("2026-02-28").date(), numeric_column="Sales",
    numeric_min=120, numeric_max=160,
)
assert len(filtered2) == 1 and float(filtered2.iloc[0]["Sales"]) == 150.0
assert apply_dashboard_filters(base, category_column="Product", categories=[]).empty
assert base.equals(source), "The source dataframe must never change during filtering."

monthly, omitted = revenue_by_period(base["Date"], base["Sales"], "Monthly")
assert omitted == 0
assert monthly["Period"].tolist() == ["2026-01", "2026-02", "2026-04"]
assert monthly["Revenue"].tolist() == [300.0, 150.0, 300.0]
assert round(float(monthly.loc[1, "Growth %"]), 2) == -50.0
assert pd.isna(monthly.loc[2, "Growth %"]), "Growth across a missing month must be undefined."

monthly2, omitted = revenue_by_period(
    pd.Series(["2026-01-01", "not-a-date", "2026-02-01"]),
    pd.Series([0, 200, 20]), "Monthly",
)
assert omitted == 1
assert pd.isna(monthly2.loc[1, "Growth %"]), "Growth after a zero previous period must be undefined."

for unit_price, variable, fixed, expected in [
    (100, 60, 800, 20),
    (100, 60, 801, 21),
    (100, 100, 200, None),
    (80, 100, 200, None),
    (90, 40, 0, 0),
    (80, 100, 0, None),
]:
    calculated = break_even_scenario(fixed, unit_price, variable)
    assert calculated["break_even_units"] == expected
assert break_even_scenario(800, 100, 60)["break_even_revenue"] == 2000
for bad_inputs in [(-10, 20, 5), (10, float("inf"), 5), (10, 20, float("nan"))]:
    try:
        break_even_scenario(*bad_inputs)
        raise AssertionError("Invalid input was not rejected")
    except ValueError:
        pass

# Integration tests use existing independent, auditable commerce metrics.
try:
    import streamlit  # noqa: F401
except ImportError:
    import sys, types
    sys.modules["streamlit"] = types.SimpleNamespace()
from commerce_engine import calculate_commercial_metrics
calcs, totals = calculate_commercial_metrics(filtered, "Sales", "Total Cost")
assert totals["net_revenue"] == 250.0
assert totals["mapped_costs"] == 135.0
assert totals["profit_after_mapped_costs"] == 115.0
assert len(calcs) == len(filtered)

# Optional: when running inside the user's project, inspect the bundled workbook.
workbook = Path(__file__).resolve().parents[1] / "data" / "business" / "Python_BI_Complete_Business_Dataset.xlsx"
if workbook.exists():
    business = pd.read_excel(workbook, sheet_name="Business Data")
    actual = apply_dashboard_filters(business, category_column="Product", categories=["Laptop"])
    if not actual.empty:
        _, real_metrics = calculate_commercial_metrics(actual, "Sales", "Total Cost")
        expected = (actual["Sales"] - actual["Total Cost"]).sum()
        assert abs(real_metrics["profit_after_mapped_costs"] - expected) < 1e-6
    print("Bundled workbook integration: PASS")

print("PASS: Filtering, same-row financial aggregation, period growth, missing periods, break-even, source immutability")

# All selected categories should be represented without mutating blank-category source rows
with_missing_category = base.copy()
with_missing_category.loc[0, "Product"] = None
unrestricted = apply_dashboard_filters(with_missing_category)
assert len(unrestricted) == len(with_missing_category)

qtr, dropped = revenue_by_period(base["Date"], base["Sales"], "Quarterly")
assert dropped == 0
assert qtr["Revenue"].tolist() == [450.0, 300.0]
