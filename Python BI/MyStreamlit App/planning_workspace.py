"""Commercial planning tools with explicit data/assumption boundaries."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from business_metrics import break_even_scenario, revenue_by_period
from performance_insights import price_sensitivity
from audit_exports import excel_safe_csv


def render_planning_workspace(data: pd.DataFrame) -> None:
    st.markdown("### Business Planning & Growth")
    st.caption(
        "Historical growth uses uploaded data. Break-even is a manual scenario; "
        "it is not a prediction of actual future performance."
    )
    growth_tab, model_tab = st.tabs(["Historical revenue growth", "Break-even scenario"])
    with growth_tab:
        numeric = data.select_dtypes(include="number").columns.tolist()
        dates = [
            col for col in data.columns
            if "date" in str(col).casefold() or "time" in str(col).casefold()
            or pd.api.types.is_datetime64_any_dtype(data[col])
        ]
        if not numeric or not dates or data.empty:
            st.info("Historical growth requires a dataset with a date field and numeric revenue field.")
        else:
            first, second, third = st.columns(3)
            with first:
                date_col = st.selectbox(
                    "Date / timestamp field", dates,
                    index=dates.index("Date") if "Date" in dates else 0,
                    key="plan_date",
                )
            with second:
                revenue_col = st.selectbox(
                    "Revenue field", numeric,
                    index=numeric.index("Sales") if "Sales" in numeric else 0,
                    key="plan_revenue",
                )
            with third:
                period = st.selectbox(
                    "Compare periods", ["Monthly", "Quarterly", "Yearly"],
                    key="plan_cadence",
                )
            st.caption(
                "Choose a revenue field that is already net of any deductions you want included. "
                "This section does not automatically deduct returns, taxes or discounts."
            )
            try:
                summary, excluded = revenue_by_period(data[date_col], data[revenue_col], period)
                if excluded:
                    st.warning(f"Excluded {excluded:,} rows without valid dates. The source dataset is unchanged.")
                if summary.empty:
                    st.info("There are no valid date/revenue records to summarise.")
                else:
                    cols = st.columns(3)
                    cols[0].metric("Periods observed", f"{len(summary):,}")
                    cols[1].metric("Observed-period revenue", f"{summary['Revenue'].sum():,.2f}")
                    valid_growth = summary["Growth %"].dropna()
                    cols[2].metric(
                        "Latest defined growth",
                        f"{valid_growth.iloc[-1]:+.2f}%" if not valid_growth.empty else "Not available",
                    )
                    st.plotly_chart(
                        px.bar(summary, x="Period", y="Revenue", title=f"Revenue by {period.lower()} period"),
                        width="stretch",
                    )
                    with st.expander("Period-level audit and growth rules"):
                        st.dataframe(summary, width="stretch", hide_index=True)
                        st.caption(
                            "Growth = (current − previous) / previous × 100. Undefined for "
                            "missing intermediate periods or prior revenue of zero/less."
                        )
                        st.download_button(
                            "Export growth analysis", summary.to_csv(index=False).encode("utf-8"),
                            file_name="python_bi_revenue_growth.csv", mime="text/csv", key="plan_growth_export",
                        )
            except (ValueError, TypeError, OverflowError) as exc:
                st.warning(f"Revenue growth is unavailable: {exc}")
    with model_tab:
        st.info(
            "Enter values for one consistent currency and unit of production. "
            "These are your scenario assumptions, not inferred amounts from the dataset."
        )
        a, b, c = st.columns(3)
        with a:
            fixed = st.number_input(
                "Fixed costs per planning period", min_value=0.0, value=0.0, step=100.0,
                key="plan_fixed",
            )
        with b:
            price = st.number_input(
                "Selling price per unit", min_value=0.0, value=0.0, step=1.0,
                key="plan_price",
            )
        with c:
            variable = st.number_input(
                "Variable cost per unit", min_value=0.0, value=0.0, step=1.0,
                key="plan_variable",
            )
        if price == 0 and variable == 0 and fixed == 0:
            st.caption("Enter your scenario assumptions above to calculate a break-even point.")
        else:
            try:
                result = break_even_scenario(fixed, price, variable)
                metrics = st.columns(3)
                metrics[0].metric("Unit contribution", f"{result['contribution_per_unit']:,.2f}")
                cm = result["contribution_margin_pct"]
                metrics[1].metric("Contribution margin", f"{cm:.2f}%" if cm is not None else "Not defined")
                units = result["break_even_units"]
                metrics[2].metric("Break-even units", f"{units:,}" if units is not None else "Not attainable")
                if units is None:
                    st.warning("There is no finite break-even volume: unit contribution is zero or negative.")
                else:
                    st.metric("Revenue at break-even units", f"{result['break_even_revenue']:,.2f}")
                st.caption(
                    "Break-even units = ceiling(fixed costs / (unit price − variable cost)). "
                    "The model assumes constant costs and price, and does not include financing, tax or capacity effects."
                )
                st.download_button(
                    "Export scenario assumptions", excel_safe_csv(pd.DataFrame([result])),
                    file_name="python_bi_break_even_scenario.csv", mime="text/csv", key="plan_break_even_export",
                )
                with st.expander("Hypothetical selling-price sensitivity", expanded=False):
                    st.caption(
                        "Illustrative ±5% and ±10% changes to selling price only; "
                        "fixed and variable costs remain constant. These are not forecasts."
                    )
                    sensitivity = price_sensitivity(fixed, price, variable)
                    st.dataframe(sensitivity, width="stretch", hide_index=True)
                    finite = sensitivity.dropna(subset=["Break-even Units"])
                    if not finite.empty:
                        st.plotly_chart(
                            px.line(
                                finite, x="Hypothetical Unit Price", y="Break-even Units",
                                markers=True, title="Break-even volume by hypothetical price",
                            ), width="stretch",
                        )
                    else:
                        st.warning("No finite break-even volume exists in these scenarios.")
                    st.download_button(
                        "Export sensitivity scenarios", excel_safe_csv(sensitivity),
                        file_name="python_bi_price_sensitivity.csv",
                        mime="text/csv", key="plan_sensitivity_export",
                    )
            except ValueError as error:
                st.warning(f"Invalid scenario: {error}")
