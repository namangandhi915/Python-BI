"""Executive overview: all metrics, trends and exports use the SAME filtered rows."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from business_metrics import apply_dashboard_filters, revenue_by_period
from commerce_engine import NONE, calculate_commercial_metrics
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
    st.caption("Want to change the graph type? Expand Section 07 · Interactive chart studio below; choose bar, line, area, donut, scatter or histogram.")
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
                category_values = sorted(data[category].dropna().astype(str).unique().tolist())
                if len(category_values) > 250:
                    st.info("This field has over 250 values; use another category for an interactive selector.")
                    category = "No category filter"
                else:
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
        numeric_filter = st.selectbox(
            "Additional numeric filter", ["No numeric filter"] + numeric,
            key="ex_number_field",
        )
        value_bounds = None
        if numeric_filter != "No numeric filter":
            series = pd.to_numeric(data[numeric_filter], errors="coerce").dropna()
            series = series[series.map(lambda v: bool(pd.notna(v)) and abs(v) != float("inf"))]
            if not series.empty:
                lower_default, upper_default = float(series.min()), float(series.max())
                n1, n2 = st.columns(2)
                with n1:
                    low = st.number_input("Minimum", value=lower_default, key=f"ex_min_{numeric_filter}")
                with n2:
                    high = st.number_input("Maximum", value=upper_default, key=f"ex_max_{numeric_filter}")
                value_bounds = (low, high)

    # A partially selected date range must not silently apply only one endpoint.
    start = end = None
    if date_col != "No date filter" and isinstance(date_bounds, (list, tuple)):
        if len(date_bounds) == 2:
            start, end = date_bounds
        else:
            st.info("Choose both endpoints to apply the date filter.")
    if value_bounds is not None and value_bounds[0] > value_bounds[1]:
        st.error("Minimum must be less than or equal to maximum.")
        return

    try:
        filtered = apply_dashboard_filters(
            data,
            # All selected means unrestricted, including source rows with missing categories.
            category_column=category if selected is not None and len(selected) < len(category_values) else None,
            categories=selected if selected is not None and len(selected) < len(category_values) else None,
            date_column=date_col if start is not None else None,
            start_date=start, end_date=end,
            numeric_column=numeric_filter if value_bounds is not None else None,
            numeric_min=value_bounds[0] if value_bounds is not None else None,
            numeric_max=value_bounds[1] if value_bounds is not None else None,
        ).reset_index(drop=True)
    except (ValueError, TypeError) as error:
        st.error(f"The filter is invalid: {error}")
        return

    st.caption(f"{len(filtered):,} of {len(data):,} records matched the filters.")
    if filtered.empty:
        st.warning("No records match. Adjust the filters to continue.")
        return

    with st.expander("02  ·  Confirm financial field mapping", expanded=True):
        a, b = st.columns(2)
        with a:
            revenue_col = st.selectbox(
                "Gross revenue field", numeric,
                index=_default(numeric, ["Sales", "Gross Revenue", "Revenue"]),
                key="ex_revenue",
            )
            cost_col = st.selectbox(
                "Cost of sales field (optional)", [NONE] + numeric,
                index=_default([NONE] + numeric, ["Total Cost", "COGS", "Cost"]),
                key="ex_cost",
            )
        with b:
            discount_col = st.selectbox("Discounts (optional)", [NONE] + numeric, key="ex_discount")
            returns_col = st.selectbox("Returns (optional)", [NONE] + numeric, key="ex_returns")
        st.caption(
            "Gross revenue must be before separately mapped discounts/returns. "
            "Do not map a field twice or treat Profit as a cost. All amounts must use one currency."
        )

    try:
        calculations, totals = calculate_commercial_metrics(
            filtered, revenue_col, cost_col, discount_col, returns_col
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
        if category != "No category filter" or text_fields:
            dimension = category if category != "No category filter" else text_fields[0]
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
            st.info("Add a text/category field to compare revenue across groups.")
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

    with st.expander("03  ·  Audit records and download", expanded=False):
        st.dataframe(filtered.head(200), width="stretch")
        output = build_financial_export(filtered, calculations)
        st.download_button(
            "Download filtered records and financial calculations",
            data=excel_safe_csv(output),
            file_name="python_bi_executive_filtered_data.csv", mime="text/csv", key="ex_export",
        )
        st.caption(
            "Export includes all matching records, not just the 200 previewed rows. "
            "Calculated fields are named BI_Gross_Revenue, BI_Net_Revenue, etc. "
            "Spreadsheet-dangerous text is protected in the exported copy."
        )

    if "Mapped Costs" in calculations.columns:
        with st.expander("04  ·  Category profitability and transaction exceptions", expanded=False):
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
    render_readiness_panel(data)

    # Phase 3 Batches 9 + 10: chart selection without leaving Executive Overview.
    render_chart_studio(filtered, calculations)
    # Intentionally source-wide and opt-in, unlike Dashboard-filtered charts.
    render_performance_lab(data)

    # Phase 3 Batches 11 + 12 — executive report uses the same filtered results.
    filter_descriptions = [f"{len(filtered):,} of {len(data):,} source records included"]
    if category != "No category filter":
        filter_descriptions.append(f"Category: {category}")
        if selected is not None:
            filter_descriptions.append(f"Selected values: {', '.join(map(str, selected[:20]))}" +
                                       (" (additional values omitted from label)" if len(selected) > 20 else ""))
    if start is not None:
        filter_descriptions.append(f"Dates {start} through {end} in {date_col}")
    if value_bounds is not None:
        filter_descriptions.append(f"{numeric_filter} from {value_bounds[0]:,.2f} to {value_bounds[1]:,.2f}")
    mapping = {"Gross revenue": revenue_col, "Cost of sales": cost_col,
               "Discounts": discount_col, "Returns": returns_col}
    render_executive_report(
        filtered, calculations, totals,
        dataset_name=dataset_name,
        mapping=mapping,
        filter_summary="; ".join(filter_descriptions),
    )

    # Phase 3 Batch 14 — optional concentration insight from filtered financial rows.
    render_portfolio_panel(filtered, calculations, totals)
