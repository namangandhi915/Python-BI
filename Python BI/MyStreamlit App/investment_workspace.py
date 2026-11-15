"""Python BI Studio — separately scoped investment analysis workspaces.

Business mode draws optional historical evidence from the current business dataset,
but all forward cash flows are provided or edited explicitly by the user.
Markets mode analyses a separate temporary historical file; it never changes
st.session_state['uploaded_df'] or the permanent Dataset Library.
"""
from __future__ import annotations

import io
import json

import pandas as pd
import streamlit as st

from forecast_panel import render_business_stress_test, render_market_research

from investment_engine import (
    evaluate_market_history,
    evaluate_project,
    summarize_business_evidence,
)


MISSING_FIELD = "— Not mapped —"


def _metric_value(value: float | None, suffix: str = "", decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}{suffix}" if value is not None else "Not available"


def _business_workspace(active_data: pd.DataFrame | None, active_name: str) -> None:
    st.subheader("Business Investment Decisions")
    st.caption("Historical evidence and forward-looking project scenarios are kept separate. No returns are guaranteed.")

    with st.expander("01 · Business dataset evidence", expanded=True):
        if not isinstance(active_data, pd.DataFrame) or active_data.empty:
            st.info("To inspect historical business evidence, activate a dataset in Data Workspace first. You can still model a standalone project scenario below.")
        else:
            st.caption(f"Active source: {active_name} · {len(active_data):,} records. These are not assumed to be annual cash flows.")
            numeric_fields = active_data.select_dtypes(include="number").columns.tolist()
            if not numeric_fields:
                st.warning("No numeric fields detected. Prepare numeric columns in Data Workspace first.")
            else:
                default_revenue = next((i for i, name in enumerate(numeric_fields) if name.lower().strip() in ("sales", "revenue", "gross revenue")), 0)
                revenue_col = st.selectbox("Observed revenue field", numeric_fields, index=default_revenue, key="ii_evidence_revenue")
                cost_options = [MISSING_FIELD] + numeric_fields
                default_cost = next((i for i, name in enumerate(cost_options) if name.lower().strip() in ("total cost", "cost", "cogs")), 0)
                cost_col = st.selectbox("Mapped cost field (optional)", cost_options, index=default_cost, key="ii_evidence_cost")
                try:
                    evidence = summarize_business_evidence(active_data, revenue_col, None if cost_col == MISSING_FIELD else cost_col)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Observed revenue", _metric_value(evidence["observed_revenue"]))
                    c2.metric("Mapped costs", _metric_value(evidence.get("observed_mapped_cost")))
                    c3.metric("Profit after mapped costs", _metric_value(evidence.get("profit_after_mapped_cost")))
                    st.caption("These are aggregates across the current dataset—not necessarily net profit, free cash flow, annual results, or an investment recommendation.")
                except (ValueError, TypeError) as exc:
                    st.error(str(exc))

    with st.expander("02 · Evaluate an investment cash-flow scenario", expanded=True):
        st.caption("Enter an initial outlay and incremental NET annual cash flows. Values are illustrative until you enter your own assumptions. Use one consistent currency/unit; no conversion is performed.")
        left, mid, right = st.columns(3)
        initial = left.number_input("Initial investment (year 0)", min_value=0.01, value=100000.0, step=1000.0, key="ii_initial")
        discount = mid.number_input("Annual discount rate (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="ii_discount")
        years = int(right.number_input("Forecast years", min_value=1, max_value=15, value=5, step=1, key="ii_years"))
        template = pd.DataFrame({
            "Year": range(1, years + 1),
            "Incremental Net Cash Flow": [0.0] * years,
        })
        edited = st.data_editor(
            template,
            disabled=["Year"],
            num_rows="fixed",
            hide_index=True,
            width="stretch",
            key=f"ii_cashflow_editor_{years}",
            column_config={
                "Incremental Net Cash Flow": st.column_config.NumberColumn(
                    "Incremental Net Cash Flow", help="Enter estimated cash flow received (+) or paid (-) in each year. Include terminal value in the last year if applicable.", format="%.2f"
                )
            },
        )
        st.caption("Cash flows start at the end of Year 1. Include salvage value and additional costs explicitly in the relevant year. Do not use sales revenue as net project cash flow without adjusting for all costs.")
        if st.button("Evaluate scenario", type="primary", key="ii_evaluate_business"):
            try:
                summary, period_rows = evaluate_project(
                    initial,
                    edited["Incremental Net Cash Flow"].tolist(),
                    discount,
                )
                k1, k2, k3 = st.columns(3)
                k1.metric("Scenario NPV", _metric_value(summary["npv"]))
                k2.metric("Scenario IRR", _metric_value(summary["irr_pct"], "%"))
                k3.metric("Simple payback (years)", _metric_value(summary["simple_payback_years"]))
                k4, k5 = st.columns(2)
                k4.metric("Discounted payback (years)", _metric_value(summary["discounted_payback_years"]))
                k5.metric("Undiscounted scenario ROI", _metric_value(summary["undiscounted_scenario_roi_pct"], "%"))
                st.caption(summary["irr_note"])
                st.dataframe(period_rows, width="stretch", hide_index=True)
                st.download_button(
                    "Download scenario audit (CSV)",
                    period_rows.to_csv(index=False).encode("utf-8-sig"),
                    file_name="python_bi_investment_scenario.csv",
                    mime="text/csv",
                    key="ii_business_export",
                )
                st.download_button(
                    "Download scenario assumptions and summary (JSON)",
                    json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"),
                    file_name="python_bi_investment_summary.json",
                    mime="application/json",
                    key="ii_business_summary_export",
                )
            except (ValueError, TypeError, OverflowError, KeyError) as exc:
                st.error(f"Cannot evaluate this scenario: {exc}")

    render_business_stress_test(initial, edited["Incremental Net Cash Flow"].tolist(), discount)


def _market_workspace() -> None:
    st.subheader("Financial-Market Historical Analysis")
    st.caption("Import your own historical market CSV/XLSX. This file is analysed temporarily and is NOT stored in the business Dataset Library.")
    uploaded = st.file_uploader(
        "Upload historical market prices (CSV or XLSX)",
        type=["csv", "xlsx"],
        key="ii_market_upload",
    )
    if uploaded is None:
        st.info("Upload a file with one date/timestamp column and one numeric, strictly positive price column. A synthetic example is provided with the update package.")
        return
    if uploaded.size > 25 * 1024 * 1024:
        st.error("File exceeds the 25 MiB market-analysis limit. Reduce the input file size.")
        return
    try:
        data = pd.read_csv(io.BytesIO(uploaded.getvalue())) if uploaded.name.lower().endswith(".csv") else pd.read_excel(io.BytesIO(uploaded.getvalue()))
    except (ValueError, OSError, ImportError, UnicodeError) as exc:
        st.error(f"Could not read market file: {exc}")
        return
    if data.empty or len(data.columns) < 2:
        st.error("The market file needs at least two columns and at least two dated records.")
        return
    st.caption(f"Temporary file: {uploaded.name} · {len(data):,} rows · {len(data.columns)} columns")
    colnames = [str(c) for c in data.columns]
    if len(set(colnames)) != len(colnames):
        st.error("Market file has duplicate column names. Rename those columns first.")
        return
    c1, c2, c3 = st.columns(3)
    default_date = next((i for i, c in enumerate(colnames) if "date" in c.lower() or "time" in c.lower()), 0)
    default_price = next((i for i, c in enumerate(colnames) if c.lower().strip() in ("adj close", "adjusted close", "close", "price")), min(1, len(colnames) - 1))
    date_col = c1.selectbox("Date field", colnames, index=default_date, key="ii_market_date")
    price_col = c2.selectbox("Price field", colnames, index=default_price, key="ii_market_price")
    freq = c3.selectbox("Observation frequency", ["Daily", "Weekly", "Monthly"], key="ii_market_frequency")
    rf = st.number_input("Assumed annual risk-free rate (%)", min_value=-50.0, max_value=100.0, value=0.0, step=0.25, key="ii_market_rf")
    try:
        summary, history = evaluate_market_history(data, date_col, price_col, freq, rf)
    except (ValueError, TypeError, OverflowError) as exc:
        st.error(str(exc))
        return

    a, b, c = st.columns(3)
    a.metric("Historical price return", _metric_value(summary["price_return_pct"], "%"))
    b.metric("Maximum observed drawdown", _metric_value(summary["max_observed_drawdown_pct"], "%"))
    c.metric("Annualized price CAGR", _metric_value(summary["annualized_price_cagr_pct"], "%"))
    d, e = st.columns(2)
    d.metric("Annualized volatility", _metric_value(summary["annualized_volatility_pct"], "%"))
    e.metric("Historical Sharpe ratio", _metric_value(summary["annualized_sharpe"]))
    st.line_chart(history.set_index("Date")[["Price"]])
    if not summary["frequency_consistent"]:
        st.warning("The date spacing does not match the selected frequency. Annualized volatility and Sharpe are suppressed.")
    if summary["observed_return_count"] < 30:
        st.info("At least 30 observed returns are required before volatility and Sharpe are displayed.")
    if summary["annualized_price_cagr_pct"] is None:
        st.info("CAGR is omitted for histories shorter than 90 calendar days.")
    st.caption("Price-only observations. Corporate actions, dividends, splits, expenses, fees, taxes, market holidays and currency changes are NOT inferred. No live pricing or investment recommendations are provided.")
    with st.expander("Historical return and drawdown audit"):
        st.dataframe(history.head(500), width="stretch", hide_index=True)
        st.download_button(
            "Download analysed historical prices (CSV)",
            history.to_csv(index=False).encode("utf-8-sig"),
            file_name="python_bi_market_history_analysis.csv",
            mime="text/csv",
            key="ii_market_export",
        )

    render_market_research(history, freq, summary["frequency_consistent"])


def render_investment_intelligence(active_business_df: pd.DataFrame | None, active_name: str = "No active business dataset") -> None:
    st.header("Investment Intelligence")
    st.caption("Evidence-led decision support with two independent modes. All estimates depend on supplied data and assumptions; no returns are promised.")
    mode = st.radio(
        "Analysis mode",
        ["Business Investment Decisions", "Financial Markets"],
        horizontal=True,
        key="ii_mode",
    )
    if mode == "Business Investment Decisions":
        _business_workspace(active_business_df, active_name)
    else:
        _market_workspace()
