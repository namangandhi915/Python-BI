"""Pure business-performance and planning functions with auditable assumptions."""
from __future__ import annotations

import pandas as pd
from business_metrics import break_even_scenario


def category_profitability(
    source: pd.DataFrame,
    calculations: pd.DataFrame,
    category: str,
) -> pd.DataFrame:
    """Calculate reconciled revenue and profit by category on identical rows.

    Missing categories are grouped as '(Missing)'. A zero net revenue has no
    defined profit margin; negative revenue is reported as such without hiding it.
    """
    if len(source) != len(calculations):
        raise ValueError("Source/calculation record count mismatch.")
    if category not in source.columns:
        raise ValueError(f"Unknown category column: {category}")
    needed = {"Net Revenue", "Mapped Costs", "Profit After Mapped Costs"}
    if not needed.issubset(calculations.columns):
        raise ValueError("Map cost-of-sales before calculating category profitability.")
    frame = pd.DataFrame({
        "Category": source[category].reset_index(drop=True).astype("string").fillna("(Missing)"),
        "Net Revenue": pd.to_numeric(calculations["Net Revenue"].reset_index(drop=True), errors="raise"),
        "Mapped Costs": pd.to_numeric(calculations["Mapped Costs"].reset_index(drop=True), errors="raise"),
        "Profit After Mapped Costs": pd.to_numeric(
            calculations["Profit After Mapped Costs"].reset_index(drop=True), errors="raise"
        ),
    })
    grouped = frame.groupby("Category", dropna=False).agg(
        Records=("Net Revenue", "size"),
        **{
            "Net Revenue": ("Net Revenue", "sum"),
            "Mapped Costs": ("Mapped Costs", "sum"),
            "Profit After Mapped Costs": ("Profit After Mapped Costs", "sum"),
        },
    ).reset_index()
    grouped["Profit Margin %"] = (
        grouped["Profit After Mapped Costs"]
        .div(grouped["Net Revenue"].where(grouped["Net Revenue"].ne(0))) * 100
    )
    return grouped.sort_values("Net Revenue", ascending=False, kind="stable").reset_index(drop=True)


def loss_making_rows(source: pd.DataFrame, calculations: pd.DataFrame) -> pd.DataFrame:
    """Return only transactions whose profit after mapped costs is negative."""
    if len(source) != len(calculations):
        raise ValueError("Source/calculation record count mismatch.")
    if "Profit After Mapped Costs" not in calculations.columns:
        raise ValueError("Cost-of-sales mapping is required to identify loss-making rows.")
    from audit_exports import build_financial_export
    full = build_financial_export(source, calculations)
    return full.loc[calculations["Profit After Mapped Costs"].reset_index(drop=True).lt(0).to_numpy()].reset_index(drop=True)


def price_sensitivity(
    fixed_costs: float,
    selling_price_per_unit: float,
    variable_cost_per_unit: float,
    percent_changes: tuple[int, ...] = (-10, -5, 0, 5, 10),
) -> pd.DataFrame:
    """Break-even across clearly labelled HYPOTHETICAL selling-price changes.

    Price and variable costs are per-unit. Fixed costs share the same period.
    These scenarios are not forecasts or predictions.
    """
    baseline = break_even_scenario(fixed_costs, selling_price_per_unit, variable_cost_per_unit)
    rows = []
    for variation in percent_changes:
        if not isinstance(variation, int) or variation < -100:
            raise ValueError("Price variations must be integer percentages >= -100.")
        hypothetical_price = baseline["unit_price"] * (1 + variation / 100)
        result = break_even_scenario(baseline["fixed_costs"], hypothetical_price,
                                     baseline["variable_cost_per_unit"])
        rows.append({
            "Price Change %": variation,
            "Hypothetical Unit Price": result["unit_price"],
            "Contribution Per Unit": result["contribution_per_unit"],
            "Break-even Units": result["break_even_units"],
            "Break-even Revenue": result["break_even_revenue"],
        })
    return pd.DataFrame(rows)
