"""Offline tests for Phase 6 investment foundation. No Streamlit or internet required."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from investment_engine import (
    evaluate_project, evaluate_market_history, summarize_business_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


class ProjectScenarioTests(unittest.TestCase):
    def test_known_npv_irr_and_payback(self):
        out, annual = evaluate_project(100, [110], 10)
        self.assertAlmostEqual(out["npv"], 0.0, places=8)
        self.assertAlmostEqual(out["irr_pct"], 10.0, places=7)
        self.assertAlmostEqual(out["simple_payback_years"], 100 / 110, places=9)
        self.assertAlmostEqual(out["discounted_payback_years"], 1.0, places=8)
        self.assertEqual(len(annual), 1)
        self.assertTrue(out["scenario_only"])

    def test_two_year_npv(self):
        out, _ = evaluate_project(100, [60, 60], 10)
        self.assertAlmostEqual(out["npv"], 4.13223140496, places=8)
        self.assertAlmostEqual(out["irr_pct"], 13.06623863, places=6)
        self.assertAlmostEqual(out["simple_payback_years"], 1 + (40 / 60), places=9)

    def test_negative_and_no_payback(self):
        out, _ = evaluate_project(100, [-10, 10, -10], 10)
        self.assertIsNone(out["simple_payback_years"])
        self.assertIsNone(out["discounted_payback_years"])
        self.assertIsNone(out["irr_pct"])

    def test_nonconventional_irr_omitted(self):
        out, _ = evaluate_project(100, [230, -132], 10)
        self.assertIsNone(out["irr_pct"])
        self.assertIn("multiple", out["irr_note"])

    def test_invalid_inputs_rejected(self):
        cases = [(0, [50], 10), (100, [], 10), (100, [float("nan")], 10), (100, [30], -100), (100, [30], float("inf"))]
        for initial, flows, rate in cases:
            with self.subTest(initial=initial, flows=flows, rate=rate), self.assertRaises(ValueError):
                evaluate_project(initial, flows, rate)


class EvidenceTests(unittest.TestCase):
    def test_valid_business_evidence(self):
        df = pd.DataFrame({"Sales": [100, 200], "Total Cost": [30, 80]})
        original = df.copy(deep=True)
        e = summarize_business_evidence(df, "Sales", "Total Cost")
        self.assertEqual(e["observed_revenue"], 300)
        self.assertEqual(e["observed_mapped_cost"], 110)
        self.assertEqual(e["profit_after_mapped_cost"], 190)
        assert_frame_equal(df, original)

    def test_missing_financial_data_fails(self):
        df = pd.DataFrame({"Sales": [100, None], "Cost": [40, 20]})
        with self.assertRaisesRegex(ValueError, "missing"):
            summarize_business_evidence(df, "Sales", "Cost")
        with self.assertRaisesRegex(ValueError, "separate"):
            summarize_business_evidence(df, "Cost", "Cost")


class MarketHistoryTests(unittest.TestCase):
    def test_price_return_and_drawdown(self):
        df = pd.DataFrame({"Date": ["2026-01-15", "2026-01-01", "2026-01-08"], "Close": [99, 100, 110]})
        original = df.copy(deep=True)
        out, series = evaluate_market_history(df, "Date", "Close", "Weekly")
        self.assertAlmostEqual(out["price_return_pct"], -1.0, places=8)
        self.assertAlmostEqual(out["max_observed_drawdown_pct"], -10.0, places=8)
        self.assertEqual(out["records"], 3)
        self.assertTrue(out["frequency_consistent"])
        self.assertIsNone(out["annualized_volatility_pct"])
        self.assertEqual(series["Price"].tolist(), [100, 110, 99])
        assert_frame_equal(df, original)

    def test_date_duplicate_and_invalid_price_rejected(self):
        duplicate = pd.DataFrame({"Date": ["2026-01-01", "2026-01-01"], "Price": [100, 101]})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate_market_history(duplicate, "Date", "Price")
        invalid = pd.DataFrame({"Date": ["2026-01-01", "2026-01-02"], "Price": [100, 0]})
        with self.assertRaisesRegex(ValueError, "Invalid rows"):
            evaluate_market_history(invalid, "Date", "Price")

    def test_daily_volatility_and_cadence(self):
        df = pd.DataFrame({
            "Date": pd.bdate_range("2026-01-01", periods=55),
            "Close": [100 + 0.4 * i + (i % 7) * 0.5 for i in range(55)],
        })
        out, _ = evaluate_market_history(df, "Date", "Close", "Daily", 2.0)
        self.assertIsNotNone(out["annualized_volatility_pct"])
        self.assertIsNotNone(out["annualized_sharpe"])
        self.assertIsNone(out["annualized_price_cagr_pct"])
        wrong, _ = evaluate_market_history(df, "Date", "Close", "Monthly")
        self.assertFalse(wrong["frequency_consistent"])
        self.assertIsNone(wrong["annualized_sharpe"])

    def test_limit_and_missing_dates_rejected(self):
        bad = pd.DataFrame({"date": ["2026-01-01", "invalid"], "price": [100, 101]})
        with self.assertRaisesRegex(ValueError, "Invalid rows"):
            evaluate_market_history(bad, "date", "price")
        with self.assertRaisesRegex(ValueError, "Frequency"):
            evaluate_market_history(bad, "date", "price", "Hourly")


class WiringTests(unittest.TestCase):
    def test_app_routes_preserved_and_added(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        ast.parse(app)
        self.assertIn('"Data Workspace"', app)
        self.assertIn('"Dashboard"', app)
        self.assertIn('"Investment Intelligence"', app)
        self.assertIn('elif page == "Investment Intelligence":', app)
        self.assertIn('render_executive_dashboard(', app)
        self.assertIn('save_active_dataset(', app)
        self.assertIn('render_investment_intelligence(', app)
        self.assertNotIn('save_active_dataset(uploaded)', (ROOT / 'modules' / 'investment_workspace.py').read_text())

    def test_no_unexpected_imports(self):
        for filename in ("investment_engine.py", "investment_workspace.py", "home_experience.py"):
            compile((ROOT / "modules" / filename).read_text(encoding="utf-8"), filename, "exec")
        compile((ROOT / "app.py").read_text(encoding="utf-8"), "app.py", "exec")


if __name__ == "__main__":
    unittest.main(verbosity=2)
