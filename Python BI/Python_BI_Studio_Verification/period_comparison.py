"""Auditable period comparisons for Python BI Studio.

Works on already-filtered source records and their positionally matched
commercial calculations; does not mutate either input. Calendar, not fiscal,
periods are used, without seasonality or business-day adjustments.
"""
from __future__ import annotations

import math
import pandas as pd

FREQUENCIES = {"Monthly": "M", "Quarterly": "Q", "Yearly": "Y"}
FINANCIAL_FIELDS = ("Gross Revenue", "Net Revenue", "Mapped Costs", "Profit After Mapped Costs")


def _period_series(source: pd.DataFrame, date_column: str, cadence: str) -> tuple[pd.Series, int]:
    if date_column not in source.columns:
        raise ValueError(f"The selected date column is missing: {date_column}")
    if cadence not in FREQUENCIES:
        raise ValueError("Select Monthly, Quarterly or Yearly.")
    # Positional index avoids accidental label alignment for datasets with repeated indices.
    date_values = pd.to_datetime(source[date_column].reset_index(drop=True), errors="coerce", format="mixed")
    invalid_count = int(date_values.isna().sum())
    try:
        periods = date_values.dt.to_period(FREQUENCIES[cadence])
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("Cannot group this date column into calendar periods. Check mixed time zones or values.") from error
    return periods, invalid_count


def available_periods(source: pd.DataFrame, date_column: str, cadence: str) -> tuple[list[str], int]:
    """Return ordered nonempty observed periods and excluded invalid-date count."""
    periods, invalid_count = _period_series(source, date_column, cadence)
    distinct = sorted(periods.dropna().unique())
    return [str(value) for value in distinct], invalid_count


def _percent_difference(base: float, newer: float) -> float | None:
    """Percentage change is not defined if the baseline is zero or negative."""
    return ((newer - base) / base * 100) if base > 0 else None


def compare_periods(
    source: pd.DataFrame,
    calculations: pd.DataFrame,
    date_column: str,
    cadence: str,
    earlier: str,
    later: str,
    category_column: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Compare two observed calendar periods on the same matched transaction rows.

    Outputs: totals table, untruncated category table, and audit metadata.
    Excludes invalid dates ONLY from this comparison. Other dashboard results
    continue to use the entire selected filtered source.
    """
    if len(source) != len(calculations):
        raise ValueError("Source and financial calculation row counts do not match.")
    if not source.columns.is_unique or not calculations.columns.is_unique:
        raise ValueError("Ambiguous duplicate column names are not supported.")
    periods, invalid_dates = _period_series(source, date_column, cadence)
    code = FREQUENCIES[cadence]
    try:
        before_period = pd.Period(earlier, freq=code)
        after_period = pd.Period(later, freq=code)
    except (ValueError, TypeError) as error:
        raise ValueError("Select two valid calendar periods.") from error
    if before_period >= after_period:
        raise ValueError("The earlier period must precede the later period.")
    before_mask = periods.eq(before_period).fillna(False).to_numpy(dtype=bool)
    after_mask = periods.eq(after_period).fillna(False).to_numpy(dtype=bool)
    if not before_mask.any() or not after_mask.any():
        raise ValueError("Both comparison periods must contain source records.")
    fields = [name for name in FINANCIAL_FIELDS if name in calculations.columns]
    if "Net Revenue" not in fields:
        raise ValueError("Financial calculations must include Net Revenue.")
    validated: dict[str, pd.Series] = {}
    for field in fields:
        values = pd.to_numeric(calculations[field].reset_index(drop=True), errors="raise")
        if values.isna().any() or not all(math.isfinite(float(v)) for v in values):
            raise ValueError(f"{field} has missing or non-finite values; comparison stopped.")
        validated[field] = values
    totals_rows = [{"Metric": "Transactions", "Earlier": int(before_mask.sum()), "Later": int(after_mask.sum())}]
    for metric in fields:
        amounts = validated[metric]
        totals_rows.append({"Metric": metric, "Earlier": float(amounts.loc[before_mask].sum()), "Later": float(amounts.loc[after_mask].sum())})
    totals = pd.DataFrame(totals_rows)
    totals["Change"] = totals["Later"] - totals["Earlier"]
    totals["Change %"] = [
        _percent_difference(float(row.Earlier), float(row.Later))
        for row in totals.itertuples(index=False)
    ]
    metadata = {
        "date_column": date_column,
        "cadence": cadence,
        "earlier": str(before_period),
        "later": str(after_period),
        "earlier_rows": int(before_mask.sum()),
        "later_rows": int(after_mask.sum()),
        "excluded_invalid_dates": invalid_dates,
        "periods_are_adjacent": bool(after_period.ordinal - before_period.ordinal == 1),
        "excluded_other_period_rows": int(len(source) - before_mask.sum() - after_mask.sum() - invalid_dates),
    }
    category_table = pd.DataFrame()
    if category_column is not None:
        if category_column not in source.columns:
            raise ValueError("Selected category field is absent.")
        category_values = source[category_column].reset_index(drop=True).astype("string").fillna("(Missing)")
        if len(category_values) != len(validated["Net Revenue"]):
            raise ValueError("Category row count does not match calculations.")
        selected_rows = before_mask | after_mask
        frame = pd.DataFrame({
            "Category": category_values.loc[selected_rows].to_numpy(),
            "Period": pd.Series(["Earlier" if hit else "Later" for hit in before_mask[selected_rows]]),
            "Net Revenue": validated["Net Revenue"].loc[selected_rows].to_numpy(dtype=float),
        })
        if "Profit After Mapped Costs" in fields:
            frame["Profit"] = validated["Profit After Mapped Costs"].loc[selected_rows].to_numpy(dtype=float)
        aggregate = frame.groupby(["Category", "Period"], dropna=False, sort=False).agg(
            Records=("Net Revenue", "size"),
            Revenue=("Net Revenue", "sum"),
            **({"Profit": ("Profit", "sum")} if "Profit" in frame else {}),
        ).unstack("Period", fill_value=0)
        category_table = pd.DataFrame({"Category": aggregate.index.astype(str)})
        for name, output_name in (("Records", "Records"), ("Revenue", "Revenue"), ("Profit", "Profit")):
            if name not in aggregate:
                continue
            for position in ("Earlier", "Later"):
                category_table[f"{position} {output_name}"] = (
                    aggregate[name][position].to_numpy()
                    if position in aggregate[name].columns else 0
                )
            category_table[f"{output_name} Change"] = category_table[f"Later {output_name}"] - category_table[f"Earlier {output_name}"]
            if output_name == "Revenue":
                category_table["Revenue Change %"] = [
                    _percent_difference(float(x), float(y)) for x, y in zip(
                        category_table["Earlier Revenue"], category_table["Later Revenue"]
                    )
                ]
        category_table = category_table.sort_values(
            "Later Revenue", ascending=False, kind="stable"
        ).reset_index(drop=True)
        # Financial audit: grouping ALL categories must reconcile to period totals.
        for position in ("Earlier", "Later"):
            expected = float(validated["Net Revenue"].loc[before_mask if position == "Earlier" else after_mask].sum())
            actual = float(category_table[f"{position} Revenue"].sum())
            if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-7):
                raise ValueError("Category comparison revenue did not reconcile; report stopped.")
    return totals, category_table, metadata
