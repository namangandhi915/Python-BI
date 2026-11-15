"""Final Phase 4 gate: make the tutorial/legacy Dashboard schema- and result-aware.

Normal workbook retains the original Detailed Analytics implementation unchanged.
For incompatible or excessively large datasets a safe, explicitly mapped summary
is shown instead of trusting column names or displaying misleading calculations.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd

LEGACY_COLUMNS = frozenset({
    "Sales", "Total Cost", "Profit", "Profit Margin (%)", "Quantity",
    "Product", "Region", "City", "Date", "ProductID", "CustomerID"
})
LEGACY_MAX_ROWS = 50_000


@dataclass(frozen=True)
class LegacyAssessment:
    compatible: bool
    reasons: tuple[str, ...]
    rows: int


def assess_legacy(data: pd.DataFrame, max_rows: int = LEGACY_MAX_ROWS) -> LegacyAssessment:
    reasons: list[str] = []
    if not isinstance(data, pd.DataFrame):
        return LegacyAssessment(False, ("No valid DataFrame was supplied.",), 0)
    if not data.columns.is_unique:
        reasons.append("Duplicate column labels cannot be interpreted safely.")
        return LegacyAssessment(False, tuple(reasons), len(data))
    missing = sorted(LEGACY_COLUMNS.difference(data.columns))
    if missing:
        reasons.append("Practice-workbook columns missing: " + ", ".join(missing))
    if data.empty:
        reasons.append("The active dataset has no records.")
    if len(data) > max_rows:
        reasons.append(f"Legacy tutorial view is limited to {max_rows:,} rows; use Executive Overview for larger datasets.")
    if not missing and not data.empty:
        numeric = {}
        for col in ("Sales", "Total Cost", "Profit", "Profit Margin (%)", "Quantity"):
            values = pd.to_numeric(data[col], errors="coerce")
            if values.isna().any() or not values.map(math.isfinite).all():
                reasons.append(f"{col} has missing, nonnumeric or infinite values.")
            else:
                numeric[col] = values.astype(float)
        if len(numeric) == 5:
            difference = (numeric["Sales"] - numeric["Total Cost"] - numeric["Profit"]).abs()
            if (difference > (0.01 + numeric["Sales"].abs() * 1e-9)).any():
                reasons.append("Precomputed Profit does not reconcile to Sales minus Total Cost.")
            zero_sales = numeric["Sales"].abs().le(1e-12)
            if zero_sales.any():
                reasons.append("The legacy Profit Margin (%) is undefined on zero-sales rows.")
            else:
                calc_margin = numeric["Profit"].div(numeric["Sales"]).mul(100)
                if (calc_margin - numeric["Profit Margin (%)"]).abs().gt(0.15).any():
                    reasons.append("Precomputed Profit Margin (%) does not reconcile to Profit / Sales.")
            if numeric["Quantity"].le(0).any():
                reasons.append("Legacy Quantity-based measures require a positive per-row quantity.")
        parsed = pd.to_datetime(data["Date"], errors="coerce", format="mixed")
        if parsed.isna().any():
            reasons.append("Date contains invalid/missing values incompatible with the legacy date filter.")
    return LegacyAssessment(not reasons, tuple(reasons), len(data))


def render_safe_details(data: pd.DataFrame, assessment: LegacyAssessment) -> None:
    """Optional compatible view of mapped data; no silent financial field guesses."""
    import streamlit as st
    import plotly.express as px
    from commerce_engine import calculate_commercial_metrics
    from business_metrics import revenue_by_period
    from audit_exports import excel_safe_csv, build_financial_export

    st.warning("The original Detailed Analytics tutorial is not suitable for this dataset. "
               "A field-mapped, bounded analysis is available below instead.")
    with st.expander("Why the legacy view was not used", expanded=True):
        for reason in assessment.reasons:
            st.write("• " + reason)
    st.caption("Existing Executive Overview remains the primary cross-dataset Dashboard. "
               "This compatible view does not change your uploaded data.")
    if data.empty or not data.columns.is_unique:
        st.info("Choose a nonempty dataset with unique source field names in Data Workspace.")
        return
    st.subheader("Compatible dataset summary")
    r1, r2, r3 = st.columns(3)
    r1.metric("Records", f"{len(data):,}")
    r2.metric("Fields", str(len(data.columns)))
    r3.metric("Missing cells", f"{int(data.isna().sum().sum()):,}")
    st.dataframe(data.head(150), width="stretch")
    st.caption("The preview is limited to 150 rows; source values have not been modified.")
    numeric = data.select_dtypes(include="number").columns.tolist()
    if not numeric:
        st.info("No numerical fields are available. Convert numeric-looking text in Prepare & Validate.")
        return
    no_field = "— Not mapped —"
    with st.expander("Map financial fields (optional)", expanded=True):
        revenue = st.selectbox("Revenue field", [no_field]+numeric, key="legacy_safe_revenue")
        cost = st.selectbox("Cost field", [no_field]+[c for c in numeric if c != revenue], key="legacy_safe_cost")
    if revenue == no_field:
        st.info("Choose a revenue field to display monetary KPIs. No currency assumptions are made.")
        return
    if cost == no_field:
        cost = None
    try:
        calculations, totals = calculate_commercial_metrics(data, revenue, cost)
    except (ValueError, TypeError, OverflowError) as exc:
        st.error(f"Mapped financial calculations stopped: {exc}")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Mapped gross revenue", f"{totals['gross_revenue']:,.2f}")
    c2.metric("Net revenue before other deductions", f"{totals['net_revenue']:,.2f}")
    c3.metric("Profit after mapped costs", f"{totals['profit_after_mapped_costs']:,.2f}" if cost else "Not available")
    st.caption("This view maps only the selected columns. Net profit, taxes, returns and currency "
               "are not inferred. Use Commercial Intelligence for complete financial mapping.")
    category_fields = [c for c in data.columns if c != revenue and (pd.api.types.is_object_dtype(data[c]) or pd.api.types.is_string_dtype(data[c]) or isinstance(data[c].dtype, pd.CategoricalDtype))]
    with st.expander("Category and period overview", expanded=False):
        if category_fields:
            category = st.selectbox("Category field", [no_field]+category_fields, key="legacy_safe_category")
            if category != no_field:
                grouped = pd.DataFrame({"Category": data[category].astype('string').fillna('(Missing)').to_numpy(),
                                        "Revenue": calculations["Net Revenue"].to_numpy()})
                grouped = grouped.groupby('Category', as_index=False, dropna=False)['Revenue'].sum().sort_values('Revenue', ascending=False).head(12)
                st.plotly_chart(px.bar(grouped, x="Category", y="Revenue"), width="stretch")
        dates = [c for c in data.columns if 'date' in str(c).casefold() or pd.api.types.is_datetime64_any_dtype(data[c])]
        if dates:
            selected_date = st.selectbox("Date field", [no_field]+dates, key="legacy_safe_date")
            if selected_date != no_field:
                try:
                    series, omitted = revenue_by_period(data[selected_date], calculations['Net Revenue'])
                    if omitted:
                        st.warning(f"{omitted:,} invalid/missing dates excluded from period chart, not KPIs.")
                    if not series.empty:
                        st.plotly_chart(px.line(series, x="Period", y="Revenue"), width="stretch")
                except (ValueError, TypeError) as exc:
                    st.warning(f"Time chart unavailable: {exc}")
    export_cap = 50_000
    if len(data) > export_cap:
        st.warning(f"Bounded CSV export: the first {export_cap:,} of {len(data):,} records only. "
                   "For full-dataset exports, use Data Workspace with its stated export limits.")
    st.download_button("Download mapped audit CSV", data=excel_safe_csv(build_financial_export(
                       data.head(export_cap), calculations.head(export_cap))),
                       file_name="python_bi_compatible_details.csv", mime="text/csv", key="legacy_safe_export")
