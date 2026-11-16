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
from local_file_guard import validate_upload

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

    with st.expander("01 · Evaluate an investment cash-flow scenario", expanded=True):
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
    try:
        upload_info = validate_upload(uploaded)
        cached = st.session_state.get("ii_market_data")
        if cached is None or cached[0] != upload_info["sha256"]:
            data = pd.read_csv(io.BytesIO(uploaded.getvalue())) if uploaded.name.lower().endswith(".csv") else pd.read_excel(io.BytesIO(uploaded.getvalue()))
            cached = (upload_info["sha256"], data)
            st.session_state["ii_market_data"] = cached
        data = cached[1]
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
    if list(data.columns) != colnames:
        data = data.copy(deep=False)
        data.columns = colnames
    c1, c2, c3 = st.columns(3)
    default_date = next((i for i, c in enumerate(colnames) if "date" in c.lower() or "time" in c.lower()), 0)
    default_price = next((i for i, c in enumerate(colnames) if c.lower().strip() in ("adj close", "adjusted close", "close", "price")), min(1, len(colnames) - 1))
    date_col = c1.selectbox("Date field", colnames, index=default_date, key="ii_market_date")
    price_col = c2.selectbox("Price field", colnames, index=default_price, key="ii_market_price")
    freq = c3.selectbox("Observation frequency", ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"], key="ii_market_frequency")
    st.caption("Quarterly and yearly analysis uses the last available price in each calendar period, including an incomplete latest period. Daily, weekly and monthly use the uploaded observations as provided.")
    rf = st.number_input("Assumed annual risk-free rate (%)", min_value=-50.0, max_value=100.0, value=0.0, step=0.25, key="ii_market_rf")
    try:
        analysis_key = (upload_info["sha256"], date_col, price_col, freq, rf, "period-end-v1")
        analysis = st.session_state.get("ii_market_analysis")
        if analysis is None or analysis[0] != analysis_key:
            summary, history = evaluate_market_history(data, date_col, price_col, freq, rf, aggregate_periods=freq in ("Quarterly", "Yearly"))
            analysis = (analysis_key, summary, history)
            st.session_state["ii_market_analysis"] = analysis
        _, summary, history = analysis
        if freq in ("Quarterly", "Yearly"):
            st.caption(f"{len(data):,} source rows grouped into {len(history):,} {freq.lower()} period-end observations.")
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
    chart_history = history if len(history) <= 5_000 else history.iloc[::max(1, (len(history) + 4_998) // 4_999)]
    if len(chart_history) < len(history):
        chart_history = pd.concat([chart_history, history.tail(1)]).drop_duplicates(subset=["Date"])
        st.caption(f"Chart displays {len(chart_history):,} regularly spaced observations; calculations use all {len(history):,} records.")
    st.line_chart(chart_history.set_index("Date")[["Price"]])
    if not summary["frequency_consistent"]:
        st.warning("The date spacing does not match the selected frequency. Annualized volatility and Sharpe are suppressed.")
    if summary["observed_return_count"] < 30:
        st.info("At least 30 observed returns are required before volatility and Sharpe are displayed.")
    if summary["annualized_price_cagr_pct"] is None:
        st.info("CAGR is omitted for histories shorter than 90 calendar days.")
    st.caption("Price-only observations. Corporate actions, dividends, splits, expenses, fees, taxes, market holidays and currency changes are NOT inferred. No live pricing or investment recommendations are provided.")
    with st.expander("Historical return and drawdown audit"):
        st.dataframe(history.head(500), width="stretch", hide_index=True)
        if st.checkbox("Prepare historical prices download", key="ii_market_prepare_export"):
            st.download_button(
                "Download analysed historical prices (CSV)",
                history.to_csv(index=False).encode("utf-8-sig"),
                file_name="python_bi_market_history_analysis.csv",
                mime="text/csv", key="ii_market_export",
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
