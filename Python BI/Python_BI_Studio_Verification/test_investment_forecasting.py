"""Unit and integration checks for Phase 6 combined Batches 3 + 4."""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from forecast_engine import (
    backtest_expanding_mean,
    evaluate_cashflow_stress,
    simulate_historical_bootstrap,
)

ROOT = Path(__file__).resolve().parent


def market_history(n: int = 121) -> pd.DataFrame:
    returns = np.array([0.006 + 0.004 * np.sin(k / 5) for k in range(1, n)], dtype=float)
    prices = np.concatenate(([100.0], 100.0 * np.cumprod(1 + returns)))
    return pd.DataFrame({"Date": pd.bdate_range("2025-01-01", periods=n, tz="UTC"), "Price": prices})


class CashflowStressTests(unittest.TestCase):
    def test_npv_scenario_reconciliation(self):
        summary, audit = evaluate_cashflow_stress(100, [110], 10, 20, 20)
        npvs = summary.set_index("Scenario")["NPV"]
        self.assertAlmostEqual(npvs["Base"], 0, places=8)
        self.assertAlmostEqual(npvs["Downside"], -20, places=8)
        self.assertAlmostEqual(npvs["Upside"], 20, places=8)
        self.assertEqual(len(audit), 3)

    def test_negative_cost_shocks_are_conservative(self):
        summary, audit = evaluate_cashflow_stress(100, [-20, 150], 10, 30, 20)
        vals = audit.pivot(index="Year", columns="Scenario", values="Incremental Net Cash Flow")
        self.assertAlmostEqual(vals.loc[1, "Downside"], -26)
        self.assertAlmostEqual(vals.loc[1, "Upside"], -16)
        self.assertAlmostEqual(vals.loc[2, "Downside"], 105)
        self.assertAlmostEqual(vals.loc[2, "Upside"], 180)
        self.assertLess(summary.iloc[0]["NPV"], summary.iloc[1]["NPV"])

    def test_invalid_stress_rejected(self):
        for case in (-1, 120, float("nan"), True):
            with self.subTest(case=case), self.assertRaises(ValueError):
                evaluate_cashflow_stress(100, [110], 10, case, 20)

    def test_invalid_cashflow_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            evaluate_cashflow_stress(100, [float("inf")], 10)


class MarketBootstrapTests(unittest.TestCase):
    def test_seed_reproducibility_and_no_mutation(self):
        source = market_history()
        baseline = source.copy(deep=True)
        a, path_a = simulate_historical_bootstrap(source, "Daily", 12, 1000, 100, 42)
        b, path_b = simulate_historical_bootstrap(source, "Daily", 12, 1000, 100, 42)
        self.assertEqual(a, b)
        assert_frame_equal(path_a, path_b)
        assert_frame_equal(source, baseline)
        self.assertEqual(len(path_a), 13)
        self.assertAlmostEqual(path_a.iloc[0]["Simulation Median"], 100)
        self.assertLessEqual(a["terminal_value_p05"], a["terminal_value_median"])
        self.assertLessEqual(a["terminal_value_median"], a["terminal_value_p95"])
        self.assertFalse(a["calibrated_prediction"])

    def test_flat_prices_return_constant_distribution(self):
        source = market_history()
        source["Price"] = 100.0
        report, paths = simulate_historical_bootstrap(source, "Daily", 20, 500, 250, 7)
        self.assertAlmostEqual(report["terminal_value_median"], 250, places=6)
        self.assertAlmostEqual(report["simulated_share_finishing_below_start_pct"], 0.0)
        self.assertTrue((paths["Simulation P05"] == 250).all())

    def test_simulated_loss_can_appear(self):
        source = market_history()
        source["Price"] = 100.0 * 0.99 ** np.arange(len(source))
        report, _ = simulate_historical_bootstrap(source, "Daily", 10, 500, 100, 7)
        self.assertAlmostEqual(report["simulated_share_finishing_below_start_pct"], 100.0)

    def test_invalid_inputs_and_bounded_resources(self):
        source = market_history()
        cases = [(0, 500, 100, 42), (61, 500, 100, 42), (12, 5001, 100, 42),
                 (12, 500, -100, 42), (12, 500, 100, -2)]
        for h, p, cap, seed in cases:
            with self.subTest(case=(h, p, cap, seed)), self.assertRaises(ValueError):
                simulate_historical_bootstrap(source, "Daily", h, p, cap, seed)
        with self.assertRaisesRegex(ValueError, "Frequency"):
            simulate_historical_bootstrap(source, "Annual")
        with self.assertRaisesRegex(ValueError, "60"):
            simulate_historical_bootstrap(source.head(55), "Daily")

    def test_invalid_historical_rows_rejected(self):
        source = market_history()
        source.loc[10, "Price"] = -1
        with self.assertRaisesRegex(ValueError, "positive"):
            simulate_historical_bootstrap(source, "Daily")
        source = market_history().iloc[::-1].reset_index(drop=True)
        with self.assertRaisesRegex(ValueError, "chronological"):
            simulate_historical_bootstrap(source, "Daily")


class ExpandingBacktestTests(unittest.TestCase):
    def test_flat_prices_both_zero_error(self):
        source = market_history()
        source["Price"] = 100.0
        summary, rows = backtest_expanding_mean(source)
        self.assertAlmostEqual(summary["mean_forecast_mae_pct_points"], 0)
        self.assertAlmostEqual(summary["flat_baseline_mae_pct_points"], 0)
        self.assertFalse(summary["mean_beats_flat_baseline_on_mae"])
        self.assertTrue((rows["Prior-Mean Forecast %"] == 0).all())

    def test_lookahead_guard(self):
        source = market_history()
        a, rows_a = backtest_expanding_mean(source)
        source.loc[source.index[-1], "Price"] *= 10
        b, rows_b = backtest_expanding_mean(source)
        # Last realized return changed, but no forecast may use that return.
        self.assertAlmostEqual(rows_a.iloc[-1]["Prior-Mean Forecast %"],
                               rows_b.iloc[-1]["Prior-Mean Forecast %"])
        self.assertAlmostEqual(rows_a.iloc[0]["Prior-Mean Forecast %"],
                               rows_b.iloc[0]["Prior-Mean Forecast %"])
        self.assertNotEqual(rows_a.iloc[-1]["Actual Period Return %"],
                            rows_b.iloc[-1]["Actual Period Return %"])
        self.assertTrue((rows_a["Prior Observations Used"] >= 40).all())
        self.assertFalse(a["machine_learning_model"])
        self.assertEqual(a["test_observations"], 60)

    def test_short_history_and_limits(self):
        source = market_history().head(50)
        with self.assertRaisesRegex(ValueError, "20 evaluation"):
            backtest_expanding_mean(source)
        with self.assertRaises(ValueError):
            backtest_expanding_mean(market_history(), 5)
        with self.assertRaises(ValueError):
            backtest_expanding_mean(market_history(), 40, 500)

    def test_monotonic_loss_pattern(self):
        source = market_history()
        source["Price"] = 100.0 * 0.99 ** np.arange(len(source))
        summary, _ = backtest_expanding_mean(source)
        self.assertLess(summary["mean_forecast_mae_pct_points"],
                        summary["flat_baseline_mae_pct_points"])


class WiringTests(unittest.TestCase):
    def test_foundation_code_preserved_and_new_panels_connected(self):
        code = (ROOT / "investment_workspace.py").read_text(encoding="utf-8")
        ast.parse(code)
        self.assertIn("render_business_stress_test(initial", code)
        self.assertIn("render_market_research(history, freq,", code)
        self.assertIn("evaluate_market_history", code)
        self.assertIn("evaluate_project", code)
        self.assertIn("io.BytesIO(uploaded.getvalue())", code)
        self.assertNotIn("save_active_dataset", code)
        for name in ("forecast_panel.py", "forecast_engine.py"):
            ast.parse((ROOT / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
