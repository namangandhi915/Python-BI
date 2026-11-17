"""Pure, audited analytic computations used by Python BI Studio.

No Streamlit dependency: can be tested independently and used in other interfaces.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

import pandas as pd


PERIOD_CODES = {"Monthly": "M", "Quarterly": "Q", "Yearly": "Y"}


def apply_dashboard_filters(
    data: pd.DataFrame,
    *,
    category_column: str | None = None,
    categories: Sequence[str] | None = None,
    date_column: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    numeric_column: str | None = None,
    numeric_min: float | None = None,
    numeric_max: float | None = None,
) -> pd.DataFrame:
    """Filter without mutating data. An explicit empty category selection matches zero rows."""
    mask = pd.Series(True, index=data.index)
    if category_column is not None and categories is not None:
        if category_column not in data.columns:
            raise ValueError(f"Unknown category column: {category_column}")
        mask &= data[category_column].astype("string").isin(list(categories)).fillna(False)
    if date_column is not None and start_date is not None and end_date is not None:
        if date_column not in data.columns:
            raise ValueError(f"Unknown date column: {date_column}")
        if start_date > end_date:
            raise ValueError("The start date cannot be later than the end date.")
        parsed = pd.to_datetime(data[date_column], errors="coerce", format="mixed")
        mask &= parsed.dt.date.between(start_date, end_date).fillna(False)
    if numeric_column is not None and numeric_min is not None and numeric_max is not None:
        if numeric_column not in data.columns:
            raise ValueError(f"Unknown numeric column: {numeric_column}")
        if numeric_min > numeric_max:
            raise ValueError("The numeric minimum cannot exceed its maximum.")
        values = pd.to_numeric(data[numeric_column], errors="coerce")
        mask &= values.between(numeric_min, numeric_max).fillna(False)
    return data.loc[mask].copy()


def revenue_by_period(
    dates: pd.Series,
    revenue: pd.Series,
    frequency: str = "Monthly",
) -> tuple[pd.DataFrame, int]:
    """Aggregate revenue and compute growth only for adjacent observed periods.

    A zero/negative prior revenue or a missing period means growth is undefined.
    Invalid/missing dates are excluded *and counted*; invalid financial inputs raise.
    """
    if frequency not in PERIOD_CODES:
        raise ValueError("Frequency must be Monthly, Quarterly or Yearly.")
    if len(dates) != len(revenue):
        raise ValueError("Date and revenue fields must have equal lengths.")
    values = pd.to_numeric(pd.Series(revenue).reset_index(drop=True), errors="coerce")
    if values.isna().any() or (~values.map(math.isfinite)).any():
        raise ValueError("Revenue contains missing or nonnumeric values. Correct these before measuring growth.")
    try:
        parsed = pd.to_datetime(pd.Series(dates).reset_index(drop=True), errors="coerce", format="mixed")
        if not pd.api.types.is_datetime64_any_dtype(parsed):
            raise ValueError("Mixed time zones or incompatible date formats")
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Date values must use compatible formats and a consistent time zone for period analysis.") from exc
    omitted = int(parsed.isna().sum())
    valid = parsed.notna()
    if not bool(valid.any()):
        return pd.DataFrame(columns=["Period", "Revenue", "Previous period revenue", "Growth %"]), omitted
    index = parsed.loc[valid].dt.to_period(PERIOD_CODES[frequency])
    aggregated = (
        pd.DataFrame({"Period": index.to_numpy(), "Revenue": values.loc[valid].to_numpy()})
        .groupby("Period", observed=True, sort=True)["Revenue"]
        .sum()
    )
    previous = aggregated.shift(1)
    ordinals = pd.Series(aggregated.index.asi8, index=aggregated.index)
    adjacent = ordinals.diff().eq(1)
    growth = (aggregated - previous) / previous * 100
    growth = growth.where(previous.gt(0) & adjacent)
    return pd.DataFrame({
        "Period": aggregated.index.astype(str),
        "Revenue": aggregated.to_numpy(dtype=float),
        "Previous period revenue": previous.to_numpy(dtype=float),
        "Growth %": growth.to_numpy(dtype=float),
    }).reset_index(drop=True), omitted


def break_even_scenario(
    fixed_costs: float,
    selling_price_per_unit: float,
    variable_cost_per_unit: float,
) -> dict[str, float | int | bool | None]:
    """Explicit manual scenario, not inferred actual performance.

    When unit contribution <= 0, no finite break-even volume exists for a positive
    fixed cost. Selling price and variable costs must be nonnegative and finite.
    """
    values = [fixed_costs, selling_price_per_unit, variable_cost_per_unit]
    try:
        costs, price, variable = map(float, values)
    except (TypeError, ValueError) as error:
        raise ValueError("Enter valid numerical scenario inputs.") from error
    if not all(math.isfinite(v) and v >= 0 for v in (costs, price, variable)):
        raise ValueError("Scenario inputs must be finite nonnegative amounts.")
    contribution = price - variable
    if contribution <= 0:
        units: int | None = None
    elif costs == 0:
        units = 0
    else:
        units = math.ceil(costs / contribution)
    return {
        "fixed_costs": costs,
        "unit_price": price,
        "variable_cost_per_unit": variable,
        "contribution_per_unit": contribution,
        "contribution_margin_pct": (contribution / price * 100) if price > 0 else None,
        "break_even_units": units,
        "break_even_revenue": units * price if units is not None else None,
        "profitable_at_any_volume": bool(costs == 0 and contribution > 0),
    }
