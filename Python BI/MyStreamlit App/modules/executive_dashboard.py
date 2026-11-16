"""Executive overview: all metrics, trends and exports use the SAME filtered rows."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from business_metrics import apply_dashboard_filters, revenue_by_period
from commerce_engine import NONE, calculate_commercial_metrics, mapping_scope
from audit_exports import build_financial_export, excel_safe_csv
from performance_insights import category_profitability, loss_making_rows
from executive_addons import render_comparison_panel, render_readiness_panel
from chart_builder import render_chart_studio, render_performance_lab
from executive_report import render_executive_report
from portfolio_panel import render_portfolio_panel


def _default(options: list[str], preferred: list[str], fallback: int = 0) -> int:
    lower = {name.casefold(): i for i, name in enumerate(options)}
    for name in preferred:
        if name.casefold() in lower:
            return lower[name.casefold()]
    return fallback


def render_executive_dashboard(data: pd.DataFrame, dataset_name: str) -> None:
    st.header("Executive Performance Dashboard")
    st.caption(f"Dataset: {dataset_name}  •  All figures on this page reflect the selected filters.")
    st.caption("Want to change the graph type? Expand Section 05 · Interactive chart studio below; choose bar, line, area, donut, scatter or histogram.")
    if data.empty:
        st.warning("The active dataset has no records.")
        return

    numeric = data.select_dtypes(include="number").columns.tolist()
    if not numeric:
        st.warning("No numeric financial fields are available. Prepare the source data first.")
        return

    text_fields = data.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    category_options = ["No category filter"] + text_fields
    date_options = ["No date filter"] + [
        col for col in data.columns
        if "date" in str(col).casefold() or "time" in str(col).casefold()
        or pd.api.types.is_datetime64_any_dtype(data[col])
    ]

    st.markdown("### Business performance")
    with st.expander("01  ·  Refine dataset", expanded=True):
        first, second = st.columns(2)
        with first:
            category = st.selectbox(
                "Category", category_options,
                index=_default(category_options, ["Product", "Region", "City"]),
                key="ex_category",
            )
            selected = None
            category_values = []
            if category != "No category filter":
                category_size = data[category].nunique(dropna=True)
                if category_size > 250:
                    st.info("This field has over 250 values; use another category for an interactive selector.")
                    category = "No category filter"
                else:
                    category_values = sorted(data[category].dropna().astype(str).unique().tolist())
                    selected = st.multiselect(
                        "Values to include", category_values, default=category_values,
                        key=f"ex_values_{category}",
                    )
        with second:
            date_col = st.selectbox(
                "Date field", date_options,
                index=_default(date_options, ["Date", "Order Date", "Transaction Date"]),
                key="ex_date_field",
            )
            date_bounds = None
            if date_col != "No date filter":
                apply_date_range = st.checkbox(
                    "Restrict records to a date range", value=False, key="ex_use_date_filter"
                )
                parsed = pd.to_datetime(data[date_col], errors="coerce", format="mixed").dropna()
                if not parsed.empty and apply_date_range:
                    date_bounds = st.date_input(
                        "Date range", value=(parsed.min().date(), parsed.max().date()),
                        min_value=parsed.min().date(), max_value=parsed.max().date(),
                        key=f"ex_date_bounds_{date_col}",
                    )
                elif parsed.empty:
                    st.warning("No valid dates are available in the selected field.")
    # A partially selected date range must not silently apply only one endpoint.
    start = end = None
    if date_col != "No date filter" and isinstance(date_bounds, (list, tuple)):
        if len(date_bounds) == 2:
            start, end = date_bounds
        else:
            st.info("Choose both endpoints to apply the date filter.")
    try:
        filtered = apply_dashboard_filters(
            data,
            # All selected means unrestricted, including source rows with missing categories.
            category_column=category if selected is not None and len(selected) < len(category_values) else None,
            categories=selected if selected is not None and len(selected) < len(category_values) else None,
            date_column=date_col if start is not None else None,
            start_date=start, end_date=end,
        ).reset_index(drop=True)
    except (ValueError, TypeError) as error:
        st.error(f"The filter is invalid: {error}")
        return

    st.caption(f"{len(filtered):,} of {len(data):,} records matched the filters.")
    if filtered.empty:
        st.warning("No records match. Adjust the filters to continue.")
        return

    mapping = st.session_state.get("commercial_mapping", {})
    scope = mapping_scope(data, str(st.session_state.get("active_data_token", dataset_name)))
    if mapping.get("scope") == scope:
        revenue_col = mapping["revenue"]
        cost_col = mapping["cost"]
        discount_col = mapping["discount"]
        returns_col = mapping["returns"]
        operating_col = mapping["operating"]
        taxes_col = mapping["taxes"]
        st.caption("Financial fields use the selected mapping in Commercial Intelligence for this dataset.")
    else:
        candidates = [col for col in numeric if str(col).casefold() in {"sales", "gross revenue", "revenue"}]
        if not candidates:
            st.info("Choose the revenue field in Data Workspace → Commercial Intelligence → Financial Performance to show the dashboard.")
            return
        revenue_col = candidates[0]
        cost_col = ([NONE] + numeric)[_default([NONE] + numeric, ["Total Cost", "COGS", "Cost"])]
        discount_col = returns_col = operating_col = taxes_col = NONE
        st.caption(f"Suggested financial fields: revenue = {revenue_col}; cost = {cost_col}. Confirm or change these in Commercial Intelligence.")

    try:
        calculations, totals = calculate_commercial_metrics(
            filtered, revenue_col, cost_col, discount_col, returns_col, operating_col, taxes_col
        )
    except (ValueError, TypeError, OverflowError) as error:
        st.error(f"Financial calculation blocked: {error}")
        return

    headline = st.columns(4)
    headline[0].metric("Matching Records", f"{len(filtered):,}")
    headline[1].metric("Gross Revenue", f"{totals['gross_revenue']:,.2f}")
    headline[2].metric("Net Revenue", f"{totals['net_revenue']:,.2f}")
    if "profit_after_mapped_costs" in totals:
        headline[3].metric("Profit after mapped costs", f"{totals['profit_after_mapped_costs']:,.2f}")
        sub = st.columns(3)
        sub[0].metric("Mapped costs", f"{totals['mapped_costs']:,.2f}")
        sub[1].metric("Net business loss", f"{totals['net_business_loss']:,.2f}")
        margin = totals["profit_margin_pct"]
        sub[2].metric("Profit margin", f"{margin:.2f}%" if margin is not None else "Not defined")
        st.caption("Profit shown here is after mapped costs; it is not labelled net profit unless all relevant costs are established.")
    else:
        headline[3].metric("Profit", "Not available")
        st.info("Map a cost-of-sales field to enable profit, loss and margin metrics.")

    chart_col, chart_col2 = st.columns(2)
    with chart_col:
        st.markdown("#### Revenue by category")
        dimension = category if category != "No category filter" else next(
            (field for field in text_fields if filtered[field].nunique(dropna=True) <= 250), None
        )
        if dimension is not None:
            chart_frame = pd.DataFrame({
                "Category": filtered[dimension].astype("string").fillna("(Missing)").to_numpy(),
                "Net Revenue": calculations["Net Revenue"].to_numpy(),
            })
            category_summary = (
                chart_frame.groupby("Category", as_index=False, dropna=False)["Net Revenue"]
                .sum().sort_values("Net Revenue", ascending=False).head(12)
            )
            st.plotly_chart(
                px.bar(category_summary, x="Category", y="Net Revenue", title="Top 12 categories"),
                width="stretch",
            )
        else:
            st.info("Select a category with at most 250 values to compare revenue across groups.")
    with chart_col2:
        st.markdown("#### Revenue trend")
        if date_col == "No date filter":
            st.info("Select a date field above to display period trends.")
        else:
            cadence = st.selectbox("Period", ["Monthly", "Quarterly", "Yearly"], key="ex_cadence")
            try:
                time_series, excluded_dates = revenue_by_period(
                    filtered[date_col], calculations["Net Revenue"], cadence
                )
                if excluded_dates:
                    st.warning(f"{excluded_dates:,} rows with invalid/missing dates were excluded from this trend only.")
                if not time_series.empty:
                    st.plotly_chart(
                        px.line(time_series, x="Period", y="Revenue", markers=True,
                                title="Net revenue by period"), width="stretch",
                    )
                    if time_series["Growth %"].notna().any():
                        st.caption("Growth is calculated only for adjacent periods with positive prior-period revenue.")
                else:
                    st.info("No valid dated records remain after filtering.")
            except ValueError as error:
                st.warning(f"Cannot calculate the trend: {error}")

    with st.expander("02  ·  Category profitability and transaction exceptions", expanded=False):
        if "Mapped Costs" not in calculations.columns:
            st.info("Map a cost-of-sales field in Commercial Intelligence to view profitability and exceptions.")
        elif st.checkbox("Calculate category profitability and exceptions", key="ex_profit_run"):
            st.caption(
                "These results use exactly the filtered records and financial field mapping above. "
                "Profit is after mapped costs; it is not necessarily accounting net profit."
            )
            available_categories = [
                c for c in filtered.columns
                if pd.api.types.is_object_dtype(filtered[c])
                or pd.api.types.is_string_dtype(filtered[c])
                or isinstance(filtered[c].dtype, pd.CategoricalDtype)
            ]
            if available_categories:
                category_field = st.selectbox(
                    "Group profitability by", available_categories,
                    index=_default(available_categories, ["Product", "Region", "City"]),
                    key="ex_profit_category",
                )
                groups = category_profitability(filtered, calculations, category_field)
                st.dataframe(groups.head(100), width="stretch", hide_index=True)
                st.download_button(
                    "Export category profitability",
                    data=excel_safe_csv(groups),
                    file_name="python_bi_category_profitability.csv",
                    mime="text/csv", key="ex_profitability_export",
                )
                st.caption(
                    "Category totals reconcile to the filtered net revenue, mapped costs "
                    "and aggregate profit above. A zero net-revenue category has undefined margin."
                )
            else:
                st.info("No categorical source field is available for grouped analysis.")
            exceptions = loss_making_rows(filtered, calculations)
            st.metric("Loss-making transactions", f"{len(exceptions):,}")
            if not exceptions.empty:
                st.dataframe(exceptions.head(100), width="stretch")
                st.download_button(
                    "Export loss-making transactions",
                    data=excel_safe_csv(exceptions),
                    file_name="python_bi_loss_making_transactions.csv",
                    mime="text/csv", key="ex_loss_export",
                )
            else:
                st.success("No transactions have a negative profit after mapped costs.")

    # Phase 3 Batches 7 + 8: optional consolidated analytical diagnostics.
    render_comparison_panel(filtered, calculations)
    with st.expander("04  ·  Column comparison and missing-value details", expanded=False):
        columns = st.multiselect("Choose two columns to compare", filtered.columns.tolist(), max_selections=2, key="dashboard_compare_columns")
        if len(columns) == 2:
            st.dataframe(filtered[columns].head(100), width="stretch")
            st.caption(f"Showing up to 100 of {len(filtered):,} filtered records.")
            missing = filtered[columns].isna().sum()
            st.dataframe(pd.DataFrame({"Column": columns, "Missing values": [int(missing[c]) for c in columns]}), hide_index=True, width="stretch")
        else:
            st.info("Select two columns to compare.")

    # Phase 3 Batches 9 + 10: chart selection without leaving Executive Overview.
    render_chart_studio(filtered, calculations)
    # Intentionally source-wide and opt-in, unlike Dashboard-filtered charts.

    # Phase 3 Batches 11 + 12 — executive report uses the same filtered results.
    filter_descriptions = [f"{len(filtered):,} of {len(data):,} source records included"]
    if category != "No category filter":
        filter_descriptions.append(f"Category: {category}")
        if selected is not None:
            filter_descriptions.append(f"Selected values: {', '.join(map(str, selected[:20]))}" +
                                       (" (additional values omitted from label)" if len(selected) > 20 else ""))
    if start is not None:
        filter_descriptions.append(f"Dates {start} through {end} in {date_col}")
    mapping = {"Gross revenue": revenue_col, "Cost of sales": cost_col,
               "Discounts": discount_col, "Returns": returns_col,
               "Operating expenses": operating_col, "Taxes": taxes_col}
    render_executive_report(
        filtered, calculations, totals,
        dataset_name=dataset_name,
        mapping=mapping,
        filter_summary="; ".join(filter_descriptions),
    )

    # Phase 3 Batch 14 — optional concentration insight from filtered financial rows.
    render_portfolio_panel(filtered, calculations, totals)
