"""Python BI Studio | investment mathematics and strictly descriptive market analytics.

No Streamlit dependency, no live prices, and no guaranteed-return claims.
All project cash flows are incremental net cash flows entered by the user.
All market prices are historical series supplied by the user; no dividends,
fees, taxes, splits, inflation adjustments, or currency translation inferred.
"""
from __future__ import annotations

from collections.abc import Sequence
from math import isfinite, sqrt

import pandas as pd
import numpy as np


FREQUENCY_PERIODS = {"Daily": 252, "Weekly": 52, "Monthly": 12, "Quarterly": 4, "Yearly": 1}


def _finite_number(value, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number, not a checkbox value.")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not isfinite(result):
        raise ValueError(f"{label} must be finite and cannot be missing.")
    return result


def _npv(initial: float, cashflows: list[float], rate: float) -> float:
    base = 1.0 + rate
    if base <= 0:
        raise ValueError("The discount rate must be above -100%.")
    return -initial + sum(amount / (base ** year) for year, amount in enumerate(cashflows, 1))


def _irr(initial: float, cashflows: list[float]) -> tuple[float | None, str]:
    # Multiple sign changes may allow multiple IRRs. Do not show an arbitrary root.
    series = [-initial] + cashflows
    nonzero = [v for v in series if v != 0]
    changes = sum((a > 0) != (b > 0) for a, b in zip(nonzero, nonzero[1:]))
    if changes == 0:
        return None, "No sign change; an IRR is not defined for these cash flows."
    if changes > 1:
        return None, "Non-conventional cash flows may have multiple IRRs; IRR is omitted."

    lo, hi = -0.999, 1.0
    f_lo = _npv(initial, cashflows, lo)
    f_hi = _npv(initial, cashflows, hi)
    while f_lo * f_hi > 0 and hi < 1_000_000:
        hi = hi * 2 + 1
        f_hi = _npv(initial, cashflows, hi)
    if f_lo * f_hi > 0:
        return None, "An IRR root could not be reliably bracketed."
    for _ in range(120):
        mid = (lo + hi) / 2
        f_mid = _npv(initial, cashflows, mid)
        if abs(f_mid) < 1e-9 or hi - lo < 1e-12:
            return mid * 100.0, "One conventional IRR root was found."
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2 * 100.0, "One conventional IRR root was found."


def _payback(initial: float, amounts: Sequence[float]) -> float | None:
    cumulative = -initial
    tolerance = 1e-10 * max(1.0, abs(initial))
    for year, amount in enumerate(amounts, start=1):
        before = cumulative
        cumulative += amount
        if before < -tolerance and cumulative >= -tolerance and amount > 0:
            return year - 1 + min(1.0, max(0.0, -before / amount))
    return None


def evaluate_project(
    initial_investment: float,
    annual_net_cash_flows: Sequence[float],
    discount_rate_pct: float,
) -> tuple[dict, pd.DataFrame]:
    """Evaluate an explicit scenario, not predict future outcomes.

    year-zero cash flow is -initial_investment; subsequent values are *net*
    incremental annual cash flows, including any terminal value in the final year.
    """
    initial = _finite_number(initial_investment, "Initial investment")
    rate_pct = _finite_number(discount_rate_pct, "Discount rate")
    if initial <= 0:
        raise ValueError("Initial investment must be greater than zero.")
    if not -99 < rate_pct <= 1000:
        raise ValueError("The discount rate must be above -99% and at most 1,000%.")
    if isinstance(annual_net_cash_flows, (str, bytes)) or not isinstance(annual_net_cash_flows, Sequence):
        raise ValueError("Provide a sequence of annual net cash flows.")
    if not 1 <= len(annual_net_cash_flows) <= 40:
        raise ValueError("Provide between one and 40 annual net cash flows.")
    flows = [_finite_number(v, f"Year {i} cash flow") for i, v in enumerate(annual_net_cash_flows, 1)]
    rate = rate_pct / 100.0
    discounted = [v / ((1 + rate) ** i) for i, v in enumerate(flows, 1)]
    cumulative = -initial
    cumulative_discounted = -initial
    records = []
    for year, (cf, discounted_cf) in enumerate(zip(flows, discounted), 1):
        cumulative += cf
        cumulative_discounted += discounted_cf
        records.append({
            "Year": year,
            "Incremental Net Cash Flow": cf,
            "Discounted Cash Flow": discounted_cf,
            "Cumulative Cash Flow": cumulative,
            "Cumulative Discounted Cash Flow": cumulative_discounted,
        })
    irr_pct, irr_note = _irr(initial, flows)
    summary = {
        "initial_investment": initial,
        "discount_rate_pct": rate_pct,
        "years": len(flows),
        "sum_of_net_cash_flows": float(sum(flows)),
        "npv": float(_npv(initial, flows, rate)),
        "undiscounted_scenario_roi_pct": (sum(flows) - initial) / initial * 100,
        "simple_payback_years": _payback(initial, flows),
        "discounted_payback_years": _payback(initial, discounted),
        "irr_pct": irr_pct,
        "irr_note": irr_note,
        "scenario_only": True,
    }
    return summary, pd.DataFrame.from_records(records)


def summarize_business_evidence(data: pd.DataFrame, revenue_col: str, cost_col: str | None = None) -> dict:
    """Read company dataset columns without assuming these cover all expenses."""
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Activate a non-empty business dataset first.")
    if revenue_col not in data.columns:
        raise ValueError("Select an available revenue column.")
    if cost_col and (cost_col not in data.columns or cost_col == revenue_col):
        raise ValueError("Select a separate, available mapped-cost column.")
    out = {"records": len(data), "revenue_field": revenue_col, "cost_field": cost_col}
    for label, column in [("observed_revenue", revenue_col), ("observed_mapped_cost", cost_col)]:
        if column is None:
            continue
        series = pd.to_numeric(data[column], errors="coerce")
        invalid = series.isna() | ~series.map(lambda x: bool(pd.notna(x)) and isfinite(float(x)))
        if invalid.any():
            raise ValueError(f"Column '{column}' contains {int(invalid.sum())} missing, invalid or non-finite values.")
        out[label] = float(series.sum())
    if cost_col:
        out["profit_after_mapped_cost"] = out["observed_revenue"] - out["observed_mapped_cost"]
    return out


def evaluate_market_history(
    data: pd.DataFrame,
    date_col: str,
    price_col: str,
    frequency: str = "Daily",
    annual_risk_free_pct: float = 0.0,
    aggregate_periods: bool = False,
) -> tuple[dict, pd.DataFrame]:
    """Descriptive *price-only* risk/return analysis on an uploaded series.

    No adjustment is inferred for dividends, splits, fees, taxes or currency.
    Annualized vol/Sharpe require >=30 observed returns and plausible date cadence.
    """
    if frequency not in FREQUENCY_PERIODS:
        raise ValueError("Frequency must be Daily, Weekly, Monthly, Quarterly, or Yearly.")
    rf_pct = _finite_number(annual_risk_free_pct, "Annual risk-free rate")
    if not -99 < rf_pct <= 100:
        raise ValueError("Annual risk-free rate must be above -99% and at most 100%.")
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Upload a non-empty historical price dataset.")
    if date_col == price_col or date_col not in data.columns or price_col not in data.columns:
        raise ValueError("Choose distinct date and price columns.")
    if len(data) > 1_000_000:
        raise ValueError("The historical analysis is limited to 1,000,000 source rows.")

    dates = pd.to_datetime(data[date_col], errors="coerce", format="mixed", utc=True)
    prices = pd.to_numeric(data[price_col], errors="coerce")
    bad_date = dates.isna()
    bad_price = prices.isna() | ~np.isfinite(prices.to_numpy(dtype=float, na_value=np.nan)) | (prices <= 0)
    if bad_date.any() or bad_price.any():
        raise ValueError(
            f"Invalid rows: {int(bad_date.sum())} with missing/unparseable dates and "
            f"{int(bad_price.sum())} with missing, non-positive or invalid prices. "
            "Correct the source data before proceeding."
        )
    if dates.duplicated().any():
        raise ValueError(f"{int(dates.duplicated().sum())} duplicate timestamps found. Resolve duplicates before analysing returns.")

    series = pd.DataFrame({"Date": dates, "Price": prices.astype(float)}, index=data.index)
    series = series.sort_values("Date").reset_index(drop=True)
    if aggregate_periods:
        if frequency not in ("Quarterly", "Yearly"):
            raise ValueError("Period aggregation is available for quarterly and yearly analysis.")
        # Keep the actual timestamp of the final observation, including incomplete periods.
        period = series["Date"].dt.tz_localize(None).dt.to_period("Q" if frequency == "Quarterly" else "Y")
        series = series.groupby(period, sort=True).tail(1).reset_index(drop=True)
    if len(series) < 2:
        raise ValueError("At least two distinct dated price periods are required for this frequency.")
    gaps = series["Date"].diff().dt.total_seconds().iloc[1:] / 86400.0
    median_gap = float(gaps.median())
    acceptable = {
        "Daily": (0.5, 4.5),
        "Weekly": (4.5, 11.5),
        "Monthly": (24, 36),
        "Quarterly": (75, 105),
        "Yearly": (330, 400),
    }
    low, high = acceptable[frequency]
    cadence_ok = low <= median_gap <= high
    series["Period Return %"] = series["Price"].pct_change(fill_method=None) * 100
    series["Drawdown %"] = (series["Price"] / series["Price"].cummax() - 1) * 100

    first, last = float(series["Price"].iloc[0]), float(series["Price"].iloc[-1])
    start_date, end_date = series["Date"].iloc[0], series["Date"].iloc[-1]
    days = (end_date - start_date).total_seconds() / 86400.0
    returns = series["Period Return %"].dropna() / 100.0
    periods = FREQUENCY_PERIODS[frequency]
    vol = sharpe = None
    if len(returns) >= 30 and cadence_ok:
        volatility = float(returns.std(ddof=1))
        vol = volatility * sqrt(periods) * 100
        periodic_rf = (1 + rf_pct / 100.0) ** (1 / periods) - 1
        if volatility > 0:
            sharpe = float((returns.mean() - periodic_rf) / volatility * sqrt(periods))
    summary = {
        "records": len(series),
        "start_date": str(start_date.date()),
        "end_date": str(end_date.date()),
        "first_price": first,
        "last_price": last,
        "price_return_pct": (last / first - 1) * 100,
        "max_observed_drawdown_pct": float(series["Drawdown %"].min()),
        "annualized_price_cagr_pct": ((last / first) ** (365.25 / days) - 1) * 100 if days >= 90 else None,
        "annualized_volatility_pct": vol,
        "annualized_sharpe": sharpe,
        "observed_return_count": len(returns),
        "observation_frequency": frequency,
        "median_gap_days": median_gap,
        "frequency_consistent": cadence_ok,
        "annual_risk_free_pct": rf_pct,
        "price_only": True,
    }
    return summary, series
