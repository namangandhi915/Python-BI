"""Python BI Studio | explicit scenario stress tests and historical research.

No live-market connection, proprietary ML claim, investment recommendation, or
promise of future returns. Market bootstrap is an IID historical-return
resampling experiment; its distribution is NOT a calibrated confidence interval.
"""
from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

import numpy as np
import pandas as pd

from investment_engine import FREQUENCY_PERIODS, evaluate_project


def _finite(value: float, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if not isfinite(number):
        raise ValueError(f"{field} must be finite.")
    return number


def evaluate_cashflow_stress(
    initial_investment: float,
    cashflows: Sequence[float],
    discount_rate_pct: float,
    downside_pct: float = 20,
    upside_pct: float = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic cash-flow shocks, not probabilistic forecasts.

    Downside = base - abs(base) * shock, so negative outflows get worse too.
    Initial project outlay is held fixed and no costs are invented.
    """
    downside = _finite(downside_pct, "Downside shock")
    upside = _finite(upside_pct, "Upside change")
    if not 0 <= downside <= 100 or not 0 <= upside <= 100:
        raise ValueError("Cash-flow shocks must be between 0 and 100 percent.")
    if isinstance(cashflows, (str, bytes)) or not isinstance(cashflows, Sequence):
        raise ValueError("Cash flows must be a sequence of annual amounts.")
    # evaluate_project performs comprehensive validation of the initial values.
    base_summary, _ = evaluate_project(initial_investment, cashflows, discount_rate_pct)
    base = [float(v) for v in cashflows]
    versions = (
        ("Downside", [v - abs(v) * downside / 100 for v in base]),
        ("Base", base),
        ("Upside", [v + abs(v) * upside / 100 for v in base]),
    )
    summaries = []
    audits = []
    for name, flows in versions:
        result, audit = evaluate_project(initial_investment, flows, discount_rate_pct)
        summaries.append({
            "Scenario": name,
            "NPV": result["npv"],
            "IRR % (if unique)": result["irr_pct"],
            "Simple Payback Years": result["simple_payback_years"],
            "Discounted Payback Years": result["discounted_payback_years"],
            "Undiscounted ROI %": result["undiscounted_scenario_roi_pct"],
            "Total Net Cash Inflows": result["sum_of_net_cash_flows"],
        })
        audit.insert(0, "Scenario", name)
        audits.append(audit)
    assert len(base_summary) > 0
    return pd.DataFrame(summaries), pd.concat(audits, ignore_index=True)


def _observed_returns(history: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Validate a chronological market-history output from evaluate_market_history."""
    if not isinstance(history, pd.DataFrame) or not {"Date", "Price"}.issubset(history.columns):
        raise ValueError("Provide validated historical Date/Price rows from Financial Markets.")
    if not 2 <= len(history) <= 100_000:
        raise ValueError("Historical price series must contain between 2 and 100,000 records.")
    dates = pd.to_datetime(history["Date"], utc=True, errors="coerce")
    prices = pd.to_numeric(history["Price"], errors="coerce").to_numpy(dtype=float)
    if dates.isna().any() or not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Historical dates and strictly positive finite prices are required.")
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("Historical timestamps must be unique and chronological.")
    # Ratio avoids pct_change's implicit forward-fill semantics.
    ratios = prices[1:] / prices[:-1]
    if not np.isfinite(ratios).all() or (ratios <= 0).any():
        raise ValueError("Historical price ratios cannot be non-finite or non-positive.")
    log_returns = np.log(ratios)
    if not np.isfinite(log_returns).all():
        raise ValueError("Observed log returns must be finite.")
    return log_returns, dates.iloc[1:].to_numpy()


def simulate_historical_bootstrap(
    history: pd.DataFrame,
    frequency: str,
    horizon_periods: int = 12,
    simulated_paths: int = 1500,
    starting_value: float = 100.0,
    seed: int = 42,
) -> tuple[dict, pd.DataFrame]:
    """Resample historical log returns IID; do not imply a reliable forecast.

    Returns per-period p05/p50/p95 of simulated *hypothetical* portfolio values.
    This is a distribution of sampled scenarios, not a predictive confidence band.
    """
    if frequency not in FREQUENCY_PERIODS:
        raise ValueError("Frequency must be Daily, Weekly or Monthly.")
    if type(horizon_periods) is not int or not 1 <= horizon_periods <= 60:
        raise ValueError("Horizon must be an integer between 1 and 60 observations.")
    if type(simulated_paths) is not int or not 500 <= simulated_paths <= 3000:
        raise ValueError("Simulations must be between 500 and 3,000 paths.")
    if type(seed) is not int or not 0 <= seed <= 2_147_483_647:
        raise ValueError("Seed must be a non-negative 32-bit integer.")
    initial = _finite(starting_value, "Hypothetical starting value")
    if initial <= 0 or initial > 1e12:
        raise ValueError("Hypothetical starting value must be above zero and no greater than one trillion.")
    log_returns, _ = _observed_returns(history)
    if len(log_returns) < 60:
        raise ValueError("At least 60 historical period returns are needed for this simulation.")
    rng = np.random.default_rng(seed)
    draws = rng.choice(log_returns, size=(simulated_paths, horizon_periods), replace=True)
    running_logs = np.cumsum(draws, axis=1)
    if np.any(running_logs > 600) or np.any(running_logs < -600):
        raise ValueError("Historical returns are too extreme for numerically stable simulation.")
    trajectory = initial * np.exp(running_logs)
    if not np.isfinite(trajectory).all():
        raise ValueError("Simulation produced non-finite outcomes; review historical data.")
    terminal = trajectory[:, -1]
    percentiles = np.quantile(trajectory, [0.05, 0.5, 0.95], axis=0)
    results = pd.DataFrame({
        "Future Observation": np.arange(0, horizon_periods + 1, dtype=int),
        "Simulation P05": np.concatenate(([initial], percentiles[0])),
        "Simulation Median": np.concatenate(([initial], percentiles[1])),
        "Simulation P95": np.concatenate(([initial], percentiles[2])),
    })
    terminal_p05, terminal_median, terminal_p95 = np.quantile(terminal, [0.05, 0.5, 0.95])
    return {
        "method": "IID bootstrap of uploaded historical log returns; descriptive what-if distribution only",
        "observed_return_count": len(log_returns),
        "observation_frequency": frequency,
        "forecast_horizon_observations": horizon_periods,
        "simulated_paths": simulated_paths,
        "seed": seed,
        "hypothetical_initial_value": initial,
        "terminal_value_p05": float(terminal_p05),
        "terminal_value_median": float(terminal_median),
        "terminal_value_p95": float(terminal_p95),
        "simulated_share_finishing_below_start_pct": float(np.mean(terminal < initial) * 100),
        "calibrated_prediction": False,
    }, results


def backtest_expanding_mean(
    history: pd.DataFrame,
    training_min: int = 40,
    max_evaluation_periods: int = 60,
) -> tuple[dict, pd.DataFrame]:
    """One-step-ahead, non-leaky return baseline vs flat-price baseline.

    The historical mean for period i uses returns [0:i], never the target i.
    Predictions are NOT trade signals or learned AI models.
    """
    if type(training_min) is not int or not 40 <= training_min <= 500:
        raise ValueError("Minimum training returns must be an integer between 40 and 500.")
    if type(max_evaluation_periods) is not int or not 20 <= max_evaluation_periods <= 200:
        raise ValueError("Evaluation periods must be an integer between 20 and 200.")
    log_returns, dates = _observed_returns(history)
    if len(log_returns) < training_min + 20:
        raise ValueError("At least 20 evaluation returns are required beyond the training window.")
    returns = np.expm1(log_returns)
    first = max(training_min, len(returns) - max_evaluation_periods)
    indices = np.arange(first, len(returns), dtype=int)
    cumulative = np.cumsum(returns, dtype=float)
    forecast = cumulative[indices - 1] / indices  # 100% past returns only
    actual = returns[indices]
    zero_baseline = np.zeros_like(actual)
    mae_model = float(np.mean(np.abs(forecast - actual)))
    mae_zero = float(np.mean(np.abs(zero_baseline - actual)))
    rmse_model = float(np.sqrt(np.mean((forecast - actual) ** 2)))
    rmse_zero = float(np.sqrt(np.mean(actual ** 2)))
    if not np.isfinite([mae_model, mae_zero, rmse_model, rmse_zero]).all():
        raise ValueError("Backtest errors must be finite.")
    rows = pd.DataFrame({
        "Observation Date": dates[indices],
        "Actual Period Return %": actual * 100.0,
        "Prior-Mean Forecast %": forecast * 100.0,
        "Flat-Price Baseline %": zero_baseline * 100.0,
        "Prior Observations Used": indices,
    })
    return {
        "test_observations": len(indices),
        "training_min": training_min,
        "mean_forecast_mae_pct_points": mae_model * 100,
        "flat_baseline_mae_pct_points": mae_zero * 100,
        "mean_forecast_rmse_pct_points": rmse_model * 100,
        "flat_baseline_rmse_pct_points": rmse_zero * 100,
        "mean_beats_flat_baseline_on_mae": bool(mae_model < mae_zero),
        "method": "Expanding-window one-step historical mean vs zero-return baseline; no look-ahead",
        "machine_learning_model": False,
    }, rows
