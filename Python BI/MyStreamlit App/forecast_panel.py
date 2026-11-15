"""Streamlit UI for transparent, on-demand investment research.

This module does not access networks, persist market uploads, or mutate the
business Dataset Library. Simulation results are hypothetical and uncalibrated.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from forecast_engine import (
    backtest_expanding_mean,
    evaluate_cashflow_stress,
    simulate_historical_bootstrap,
)


def render_business_stress_test(
    initial: float, annual_flows: list[float], discount_rate_pct: float
) -> None:
    with st.expander("03 · Business scenario stress tests (not forecasts)", expanded=False):
        st.caption(
            "Vary the NET annual cash flows you entered above. Downside makes positive "
            "cash flows smaller and negative cash flows more negative; upside does the "
            "reverse. Initial investment and discount rate remain fixed. These are "
            "user-defined what-if scenarios, NOT predicted probabilities."
        )
        left, right = st.columns(2)
        downside = left.number_input(
            "Downside cash-flow stress (%)", min_value=0.0, max_value=100.0,
            value=20.0, step=5.0, key="ii_stress_downside"
        )
        upside = right.number_input(
            "Upside cash-flow improvement (%)", min_value=0.0, max_value=100.0,
            value=20.0, step=5.0, key="ii_stress_upside"
        )
        try:
            summary, audit = evaluate_cashflow_stress(
                initial, annual_flows, discount_rate_pct, downside, upside
            )
            st.dataframe(summary, width="stretch", hide_index=True)
            st.download_button(
                "Export three-scenario summary (CSV)",
                summary.to_csv(index=False).encode("utf-8-sig"),
                file_name="python_bi_business_stress_scenarios.csv",
                mime="text/csv", key="ii_stress_summary_export",
            )
            st.download_button(
                "Export annual scenario audit (CSV)",
                audit.to_csv(index=False).encode("utf-8-sig"),
                file_name="python_bi_business_stress_audit.csv",
                mime="text/csv", key="ii_stress_audit_export",
            )
            st.caption("No scenario is a guaranteed, expected, or AI-predicted return.")
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            st.warning(f"The scenario cannot be calculated: {exc}")


def render_market_research(history: pd.DataFrame, frequency: str, cadence_ok: bool) -> None:
    with st.expander("03 · Forecasting research — historical bootstrap and backtest", expanded=False):
        st.warning(
            "Experimental research only. Resampling past price returns is NOT a calibrated "
            "prediction, a market forecast, or an investment recommendation. The expanding-mean "
            "backtest is a simple statistical baseline, not a trained AI model."
        )
        if not cadence_ok:
            st.info(
                "The selected observation frequency does not match the dates. "
                "Correct the frequency before running annualization-dependent research."
            )
            return
        if len(history) - 1 < 60:
            st.info("At least 60 observed period returns are required for this research lab.")
            return
        left, middle, right = st.columns(3)
        horizon = int(left.number_input(
            "Future observation periods", min_value=1, max_value=60, value=12,
            step=1, key="ii_mc_horizon",
        ))
        paths = int(middle.selectbox(
            "Simulation paths", [500, 1000, 1500, 2000, 3000],
            index=2, key="ii_mc_paths",
        ))
        hypothetical_value = right.number_input(
            "Hypothetical starting value", min_value=0.01, max_value=1e12,
            value=100.0, step=10.0, key="ii_mc_initial",
        )
        seed = int(st.number_input(
            "Repeatable random seed", min_value=0, max_value=2147483647,
            value=42, step=1, key="ii_mc_seed",
        ))
        st.caption(
            f"Each period is one {frequency.lower()} observation, not necessarily one calendar "
            "day/week/month. Results assume IID reuse of uploaded historical returns, "
            "ignore dividend income, fees, taxes, currency changes and unobserved risks."
        )
        # Hash source AND controls: stale results never masquerade as new-input results.
        row_hash = pd.util.hash_pandas_object(
            history[["Date", "Price"]], index=False
        ).to_numpy(dtype="uint64").tobytes()
        options = (frequency, horizon, paths, float(hypothetical_value), seed)
        signature = hashlib.sha256(row_hash + repr(options).encode("utf-8")).hexdigest()
        if st.button("Run historical simulation and out-of-sample test", key="ii_mc_run"):
            try:
                simulation, paths_df = simulate_historical_bootstrap(
                    history, frequency, horizon, paths, hypothetical_value, seed
                )
                backtest, backtest_rows = backtest_expanding_mean(history)
                st.session_state["ii_mc_result"] = (
                    simulation, paths_df, backtest, backtest_rows
                )
                st.session_state["ii_mc_signature"] = signature
            except (ValueError, TypeError, OverflowError, KeyError) as exc:
                st.session_state.pop("ii_mc_result", None)
                st.session_state.pop("ii_mc_signature", None)
                st.error(f"Research cannot be calculated: {exc}")
        if st.session_state.get("ii_mc_signature") != signature:
            st.info("Run the research test to view results for the current source and settings.")
            return
        saved = st.session_state.get("ii_mc_result")
        if not saved:
            return
        simulation, paths_df, backtest, backtest_rows = saved
        st.markdown("#### Historical bootstrap: hypothetical terminal values")
        c1, c2, c3 = st.columns(3)
        c1.metric("Simulation P05", f"{simulation['terminal_value_p05']:,.2f}")
        c2.metric("Simulation median", f"{simulation['terminal_value_median']:,.2f}")
        c3.metric("Simulation P95", f"{simulation['terminal_value_p95']:,.2f}")
        st.metric(
            "Simulated paths finishing below starting value",
            f"{simulation['simulated_share_finishing_below_start_pct']:.1f}%",
        )
        st.line_chart(paths_df.set_index("Future Observation"))
        st.caption(
            "P05–P95 describes only the middle 90% of these simulated paths; "
            "it is not a statistically validated 90% real-world prediction interval. "
            "Simulation shares are not actual future loss probabilities."
        )
        st.download_button(
            "Download simulation distribution (CSV)",
            paths_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="python_bi_market_bootstrap.csv",
            mime="text/csv", key="ii_mc_paths_export",
        )
        st.markdown("#### Historical out-of-sample backtest")
        a, b = st.columns(2)
        a.metric("Past-only mean model MAE (percentage points)",
                 f"{backtest['mean_forecast_mae_pct_points']:.4f}")
        b.metric("Flat-price baseline MAE (percentage points)",
                 f"{backtest['flat_baseline_mae_pct_points']:.4f}")
        if not backtest["mean_beats_flat_baseline_on_mae"]:
            st.info("On this test window the simple model did not beat the flat-price baseline by MAE.")
        else:
            st.info("The simple model beat the flat-price baseline on this test window only; future results may differ.")
        st.caption(
            f"{backtest['test_observations']} evaluation observations, each forecast "
            "uses earlier returns only. No trading costs, slippage, dividends or model "
            "selection correction are included."
        )
        st.line_chart(
            backtest_rows.set_index("Observation Date")[[
                "Actual Period Return %", "Prior-Mean Forecast %", "Flat-Price Baseline %"
            ]]
        )
        with st.expander("Review out-of-sample observations"):
            st.dataframe(backtest_rows, width="stretch", hide_index=True)
        st.download_button(
            "Download backtest observations (CSV)",
            backtest_rows.to_csv(index=False).encode("utf-8-sig"),
            file_name="python_bi_market_backtest.csv",
            mime="text/csv", key="ii_mc_backtest_export",
        )
        st.download_button(
            "Download research assumptions and metrics (JSON)",
            json.dumps({"simulation": simulation, "backtest": backtest},
                       indent=2, allow_nan=False).encode("utf-8"),
            file_name="python_bi_forecasting_research.json",
            mime="application/json", key="ii_mc_json_export",
        )
