# Python BI Studio — Phase 6 Forecasting Research: Model Card

## What is included

**Business scenario stress testing.** Applies an explicitly selected downside or upside change to user-entered *net incremental* annual cash flows. It calculates NPV, IRR (if unique), payback, and scenario ROI through the existing investment engine. Cases are deterministic illustrations, not predicted returns or case probabilities.

**Financial-market historical bootstrap.** Resamples observed historical log-price returns **independently with replacement** to create a bounded distribution of hypothetical future *value trajectories* from a user-entered starting amount. It shows simulated 5th, 50th, and 95th percentiles and the fraction of simulated paths below the starting amount. It is not a trained ML/AI model, confidence interval, real-world loss probability, or a reliable forecast.

**Historical expanding-window backtest.** Compares a simple one-step historical-mean-return forecast with a zero-return/flat-price baseline. Each prediction uses **only earlier returns**; the realization for that date is excluded from training. Reports MAE and RMSE in percentage points. It does not account for data/vendor selection, data cleaning biases, overfitting from model choice, dividends, trade slippage, or transaction expenses. Outperforming a baseline on one historical sample is not predictive of future outperformance.

## Technical safeguards

- At least 60 historical returns, correctly declared daily/weekly/monthly observation spacing; upstream parser rejects duplicates, invalid dates and nonpositive prices.
- Bounded simulation 500–3000 paths and 1–60 observations; bounded numerical inputs; user-selectable deterministic seed for reproducibility.
- No network access, no automatic live market feed, and no changes to active business Dataset Library.
- Market uploaded history is held temporarily in the current session; the new module only caches small derived outputs in Streamlit session state for download stability.
- Results are invalidated when the validated historical price series or simulation controls change.
- Price-only history: splits, distributions, currency conversion, corporate actions, commissions and taxes are not inferred.
- Scenario shock is applied as base_flow +/- abs(base_flow)*percentage; a downside makes negative flows worse.

## Not included yet

- Calibrated forward predictive intervals, live market-data provider integration, time-series ML model fitting/selection, robust multi-instrument portfolio optimisation, regulatory or fiduciary advice, and audited end-to-end large-file website performance.
- No guarantee of capital preservation, gains, or investment performance.

Use this feature for exploratory analysis and software testing, not to make unreviewed financial decisions.
