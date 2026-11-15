"""Reconciled within-dataset category concentration. No market-share inference.

Functions are deterministic and do not mutate source datasets.
"""
from __future__ import annotations
import math
import pandas as pd

TOLERANCE = 0.01
MAX_GROUPS = 10000


def _finite_series(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame:
        raise ValueError(f"Missing financial field: {name}.")
    series = pd.to_numeric(frame[name].reset_index(drop=True), errors="coerce")
    if series.isna().any() or not series.map(math.isfinite).all():
        raise ValueError(f"Invalid or missing financial values in {name}.")
    return series.astype(float)


def build_category_concentration(
    source: pd.DataFrame, calculations: pd.DataFrame,
    totals: dict, category: str,
) -> dict:
    """Calculate grouped revenue/profit and optional nonnegative revenue shares.

    Shares are within THIS filtered dataset only; not total addressable market share.
    Negative category revenue disables percentage concentration calculations.
    """
    if source.empty or len(source) != len(calculations):
        raise ValueError("The source and calculation rows must be nonempty and aligned.")
    if category not in source or not source.columns.is_unique or not calculations.columns.is_unique:
        raise ValueError("Choose a valid, uniquely named category column.")
    grouped_label = source[category].reset_index(drop=True).astype("string").fillna("(Missing)")
    if grouped_label.nunique() > MAX_GROUPS:
        raise ValueError("Over 10,000 categories; narrow the filter for a meaningful comparison.")
    revenue = _finite_series(calculations, "Net Revenue")
    frame = pd.DataFrame({"Category": grouped_label, "Net Revenue": revenue})
    cost_mapped = "Mapped Costs" in calculations and "Profit After Mapped Costs" in calculations
    if cost_mapped:
        frame["Mapped Costs"] = _finite_series(calculations, "Mapped Costs")
        frame["Profit After Mapped Costs"] = _finite_series(calculations, "Profit After Mapped Costs")
    amounts = [col for col in frame.columns if col != "Category"]
    groups = (frame.groupby("Category", as_index=False, dropna=False)[amounts]
              .sum().sort_values("Net Revenue", ascending=False, kind="stable")
              .reset_index(drop=True))
    for group_col, total_key in (
        ("Net Revenue", "net_revenue"),
        ("Mapped Costs", "mapped_costs"),
        ("Profit After Mapped Costs", "profit_after_mapped_costs"),
    ):
        if group_col not in groups:
            continue
        expected = totals.get(total_key)
        if expected is None:
            raise ValueError(f"Missing total for reconciliation: {total_key}.")
        expected = float(expected)
        if not math.isfinite(expected) or not math.isclose(
            float(groups[group_col].sum()), expected, rel_tol=1e-10, abs_tol=TOLERANCE
        ):
            raise ValueError(f"Category {group_col} does not reconcile to Dashboard totals.")
    total_revenue = float(groups["Net Revenue"].sum())
    share_valid = total_revenue > 0 and not (groups["Net Revenue"] < -1e-9).any()
    metrics = {
        "category_count": len(groups), "total_net_revenue": total_revenue,
        "concentration_available": share_valid,
        "cost_mapped": cost_mapped,
        "top_category": str(groups.iloc[0]["Category"]),
        "top_category_share_pct": None,
        "top_three_share_pct": None,
        "categories_to_80_pct": None,
        "concentration_index": None,
    }
    notes = ["Shares measure distribution across the filtered records, not the wider market."]
    if share_valid:
        fractions = groups["Net Revenue"] / total_revenue
        groups["Revenue Share %"] = (fractions * 100).round(3)
        groups["Cumulative Revenue Share %"] = (fractions.cumsum() * 100).round(3)
        metrics.update(
            top_category_share_pct=float(fractions.iloc[0] * 100),
            top_three_share_pct=float(fractions.head(3).sum() * 100),
            categories_to_80_pct=int((fractions.cumsum() < .8 - 1e-12).sum() + 1),
            concentration_index=float((fractions ** 2).sum() * 10000),
        )
        notes.append("The concentration index runs from near 0 to 10,000; it is not a market HHI.")
    else:
        notes.append(
            "Revenue percentages were omitted because at least one category has negative "
            "net revenue, or total net revenue is not positive."
        )
    return {"groups": groups, "metrics": metrics, "notes": notes}
