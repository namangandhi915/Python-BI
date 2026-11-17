"""Python BI Studio — auditable commercial metrics and safe financial-field mapping."""
from __future__ import annotations

import pandas as pd
import numpy as np
import hashlib
import streamlit as st

NONE = "— Not provided —"


def mapping_scope(data: pd.DataFrame, name: str) -> str:
    """Bind field choices to the active source and its schema."""
    schema = (name, tuple((str(column), str(dtype)) for column, dtype in data.dtypes.items()))
    return hashlib.sha256(repr(schema).encode("utf-8")).hexdigest()


def _numeric(data: pd.DataFrame, column: str | None) -> pd.Series:
    """Never silently turn malformed or missing financial numbers into zero."""
    if not column or column == NONE:
        return pd.Series(0.0, index=data.index, dtype="float64")
    values = pd.to_numeric(data[column], errors="coerce")
    invalid = values.isna() | ~np.isfinite(values.to_numpy(dtype=float, na_value=np.nan))
    if invalid.any():
        raise ValueError(
            f"Financial field '{column}' has {int(invalid.sum()):,} missing or invalid "
            "values. Review these records in Prepare & Validate before calculating."
        )
    return values.astype("float64")


def calculate_commercial_metrics(
    data: pd.DataFrame,
    revenue: str,
    cost: str | None = None,
    discount: str | None = None,
    returns: str | None = None,
    operating_expenses: str | None = None,
    taxes: str | None = None,
    invested_capital: str | None = None,
    complete_costs: bool = False,
    capital_is_row_additive: bool = False,
    revenue_basis: str = "gross",
) -> tuple[pd.DataFrame, dict]:
    """Returns row-level audit and totals. All monetary fields must be same currency.

    Gross revenue must be before separately mapped discounts/returns. Mapped cost
    fields cannot overlap. ROI only uses capital mapped per row if the user explicitly
    confirms those capital amounts can be summed across transactions.
    """
    if revenue not in data.columns:
        raise ValueError("Choose a valid revenue column.")
    if revenue_basis not in ("gross", "net"):
        raise ValueError("Choose a gross or net revenue basis.")
    if revenue_basis == "net" and any(v and v != NONE for v in (discount, returns)):
        raise ValueError("Do not deduct discounts or returns again from already-net revenue.")
    if not data.columns.is_unique:
        raise ValueError("Duplicate source column names prevent reliable financial mapping.")
    if (not cost or cost == NONE) and any(field and field != NONE for field in (operating_expenses, taxes)):
        raise ValueError("Map a cost-of-sales column before mapping operating expenses or taxes. "
                         "Those expenses must not be silently excluded from profit calculations.")
    columns = [v for v in [revenue, cost, discount, returns, operating_expenses, taxes, invested_capital]
               if v and v != NONE]
    if len(columns) != len(set(columns)):
        raise ValueError("One column is mapped to multiple financial roles. Choose distinct fields.")
    output = pd.DataFrame(index=data.index)
    revenue_values = _numeric(data, revenue)
    if revenue_basis == "gross":
        output["Gross Revenue"] = revenue_values
    output["Discounts"] = _numeric(data, discount)
    output["Returns"] = _numeric(data, returns)
    output["Net Revenue"] = revenue_values - output["Discounts"] - output["Returns"]
    has_cost = bool(cost and cost != NONE)
    if has_cost:
        output["Mapped Costs"] = (
            _numeric(data, cost) + _numeric(data, operating_expenses) + _numeric(data, taxes)
        )
        output["Profit After Mapped Costs"] = output["Net Revenue"] - output["Mapped Costs"]
        output["Loss After Mapped Costs"] = (-output["Profit After Mapped Costs"]).clip(lower=0)
    totals = {
        "records": len(data),
        "total_discounts": float(output["Discounts"].sum()),
        "total_returns": float(output["Returns"].sum()),
        "net_revenue": float(output["Net Revenue"].sum()),
    }
    if revenue_basis == "gross":
        totals["gross_revenue"] = float(output["Gross Revenue"].sum())
    if has_cost:
        profit = float(output["Profit After Mapped Costs"].sum())
        totals.update({
            "mapped_costs": float(output["Mapped Costs"].sum()),
            "profit_after_mapped_costs": profit,
            "loss_after_mapped_costs": float(output["Loss After Mapped Costs"].sum()),
            "net_business_loss": max(-profit, 0.0),
            "profit_margin_pct": (
                profit / totals["net_revenue"] * 100 if totals["net_revenue"] else None
            ),
        })
        if complete_costs:
            totals["net_profit"] = profit
            if invested_capital and invested_capital != NONE and capital_is_row_additive:
                invested = float(_numeric(data, invested_capital).sum())
                totals["invested_capital"] = invested
                totals["roi_pct"] = profit / invested * 100 if invested > 0 else None
    return output, totals


def _field_selector(label: str, fields: list[str], key: str, keywords: list[str], required=False) -> str:
    options = [NONE] + fields
    default = 0
    for i, field in enumerate(options):
        if field == NONE:
            continue
        normalized = field.lower().replace("_", " ")
        if any(normalized == word for word in keywords):
            default = i
            break
    return st.selectbox(label, options, index=default, key=key)


def render_commercial_intelligence(data: pd.DataFrame) -> None:
    st.subheader("Commercial Intelligence")
    st.caption("Map source columns, examine calculation rules, then export an auditable result.")
    if data.empty:
        st.warning("The active dataset is empty.")
        return
    fields = data.select_dtypes(include="number").columns.tolist()
    if not fields:
        st.warning("No numeric source columns detected. Correct numeric-looking text in the source file and upload it again.")
        return

    scope = mapping_scope(data, str(st.session_state.get("active_data_token", st.session_state.get("uploaded_name", "Active dataset"))))
    saved = st.session_state.get("commercial_mapping", {})
    if saved.get("scope") == scope:
        for role, key in {"revenue":"ci_revenue", "cost":"ci_cost", "discount":"ci_discount", "returns":"ci_returns", "operating":"ci_opex", "taxes":"ci_taxes", "capital":"ci_capital"}.items():
            choice = saved.get(role)
            if key not in st.session_state and (choice in fields or (role != "revenue" and choice == NONE)):
                st.session_state[key] = choice

    with st.expander("Financial source mapping", expanded=True):
        left, right = st.columns(2)
        with left:
            revenue = _field_selector("Revenue (required)", fields, "ci_revenue", ["sales", "revenue", "gross revenue"], True)
            net_named = revenue != NONE and "net" in str(revenue).lower().replace("_", " ").split()
            basis_key = f"ci_revenue_basis_{scope}_{revenue}"
            basis = st.radio("Revenue basis", ["Gross (before discounts and returns)", "Net (already adjusted)"], index=1 if net_named else 0, key=basis_key, horizontal=True)
            cost = _field_selector("Cost of sales", fields, "ci_cost", ["total cost", "cost", "cogs"])
            if basis.startswith("Net"):
                discount = returns = NONE
                st.caption("Discounts and returns are already included in net revenue and will not be deducted again.")
            else:
                discount = _field_selector("Discounts (optional)", fields, "ci_discount", ["discounts", "discount amount"])
                returns = _field_selector("Returns / refunds (optional)", fields, "ci_returns", ["returns", "refunds"])
        with right:
            operating = _field_selector("Operating expenses (optional)", fields, "ci_opex", ["operating expenses", "opex"])
            taxes = _field_selector("Taxes (optional)", fields, "ci_taxes", ["taxes", "tax expense"])
            capital = _field_selector("Invested capital (optional)", fields, "ci_capital", ["invested capital", "capital invested"])
        complete = st.checkbox(
            "I confirm mapped costs include all relevant expenses and taxes required to report net profit",
            key="ci_complete_costs"
        )
        capital_additive = st.checkbox(
            "I confirm invested capital is an independent, additive amount in each row (not a repeated account balance)",
            key="ci_capital_additive"
        ) if capital != NONE else False
        st.info("Choose whether revenue is gross or already net. Do not map overlapping columns or deduct adjustments twice.")

    if revenue == NONE:
        st.session_state.pop("commercial_mapping", None)
        st.info("Select a revenue field to calculate commercial metrics; no unrelated numeric field is selected automatically.")
        return

    try:
        calculated, m = calculate_commercial_metrics(
            data, revenue, cost, discount, returns, operating, taxes, capital,
            complete, capital_additive, revenue_basis="net" if basis.startswith("Net") else "gross"
        )
    except (ValueError, TypeError, OverflowError) as exc:
        if saved.get("scope") == scope:
            st.session_state.pop("commercial_mapping", None)
        st.error(str(exc))
        return

    is_net = basis.startswith("Net")
    st.session_state["commercial_mapping"] = {"scope": scope, "revenue": revenue, "basis": "net" if is_net else "gross", "cost": cost, "discount": discount, "returns": returns, "operating": operating, "taxes": taxes, "capital": capital}
    left, right = st.columns(2)
    left.metric("Gross Revenue", "Not provided" if is_net else f"{m['gross_revenue']:,.2f}")
    right.metric("Net Revenue", f"{m['net_revenue']:,.2f}")
    if "mapped_costs" not in m:
        st.warning("Choose a cost-of-sales column to calculate profit, loss and margin.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Mapped Costs", f"{m['mapped_costs']:,.2f}")
        c2.metric("Profit After Mapped Costs", f"{m['profit_after_mapped_costs']:,.2f}")
        c3.metric("Net Business Loss", f"{m['net_business_loss']:,.2f}")
        st.caption(f"Sum of losses on individual rows: {m['loss_after_mapped_costs']:,.2f}. This differs from net business loss.")
        margin = m["profit_margin_pct"]
        st.metric("Profit Margin After Mapped Costs", f"{margin:.2f}%" if margin is not None else "Not defined")
    if "net_profit" in m:
        col_a, col_b = st.columns(2)
        col_a.metric("Net Profit (confirmed)", f"{m['net_profit']:,.2f}")
        roi = m.get("roi_pct")
        col_b.metric("ROI (confirmed investment basis)", f"{roi:.2f}%" if roi is not None else "Not available")
    else:
        st.caption("Net Profit and ROI remain unavailable until the required assumptions are confirmed.")
    date_fields = [c for c in data.columns if "date" in str(c).casefold() or "time" in str(c).casefold() or pd.api.types.is_datetime64_any_dtype(data[c])]
    if date_fields:
        from business_metrics import revenue_by_period
        import plotly.express as px
        with st.expander("Net revenue by period", expanded=False):
            date_field = st.selectbox("Revenue trend date field", date_fields, key="ci_trend_date")
            cadence = st.selectbox("Revenue trend period", ["Monthly", "Quarterly", "Yearly"], key="ci_trend_period")
            try:
                series, excluded = revenue_by_period(data[date_field], calculated["Net Revenue"], cadence)
                if excluded:
                    st.caption(f"{excluded:,} records with invalid dates excluded.")
                if not series.empty:
                    st.plotly_chart(px.line(series, x="Period", y="Revenue", title="Net revenue by period"), width="stretch")
            except (ValueError, TypeError, OverflowError) as error:
                st.warning(f"Revenue trend is unavailable: {error}")

    with st.expander("Calculation notes and interpretation"):
        st.markdown("""
- Net revenue is the mapped net amount, or gross revenue minus separately mapped discounts and returns.
- Profit after mapped costs = net revenue − cost of sales − mapped operating expenses − mapped taxes.
- Net business loss = max(negative aggregate profit, 0). Row-level loss totals are reported separately.
- Net profit is shown only when users confirm all relevant costs and taxes are included.
- ROI uses confirmed net profit / sum of independently additive invested-capital amounts. It is **not** available if capital is a repeated balance.
- All monetary amounts must use the same currency. This tool does not infer missing amounts or convert currencies.
- Null, malformed or infinite values in mapped financial fields block the calculation until fixed.
        """)
    with st.expander("Audit individual calculations and export"):
        show_all = st.checkbox("Show all calculated entries", key="ci_audit_all")
        audit_limit = int(st.number_input("Calculated entries to show", min_value=1, max_value=1_000_000, value=200, step=100, key="ci_audit_limit"))
        st.dataframe(calculated if show_all else calculated.head(audit_limit), width="stretch")
        if st.checkbox("Prepare calculated metrics download", key="ci_prepare_export"):
            st.download_button(
                "Download calculated metrics", calculated.to_csv(index=False).encode("utf-8"),
                file_name="python_bi_commercial_metrics.csv", mime="text/csv", key="ci_export"
            )
