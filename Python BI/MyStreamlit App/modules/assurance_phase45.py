"""Phase 4/5 automated acceptance: independent, explicit calculation fixtures.

This suite does not imply approval of arbitrary third-party business datasets.
Any failure is captured as FAIL; unresolved UI/user checks remain MANUAL.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from math import isclose
import pandas as pd

@dataclass
class Check:
    id: str
    area: str
    status: str
    detail: str

    def as_dict(self) -> dict:
        return asdict(self)


def _run(id: str, area: str, fn) -> Check:
    try:
        detail = fn()
        return Check(id, area, 'PASS', str(detail or 'Verified'))
    except Exception as exc:
        return Check(id, area, 'FAIL', f'{type(exc).__name__}: {exc}')


def _near(actual, expected, msg) -> None:
    if not isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-8):
        raise AssertionError(f'{msg}: expected {expected}, found {actual}')


def fixture() -> pd.DataFrame:
    return pd.DataFrame({
        'Product': ['A', 'B', 'A', 'B'],
        'Sales': [100.0, 200.0, 50.0, 150.0],
        'Cost': [40.0, 120.0, 30.0, 90.0],
        'Discounts': [10.0, 0.0, 5.0, 0.0],
        'Returns': [0.0, 20.0, 0.0, 0.0],
        'Date': pd.to_datetime(['2026-01-01', '2026-01-09', '2026-02-01', '2026-02-12']),
    })


def run_phase45_checks() -> list[Check]:
    # Streamlit is imported by the existing UI wrapper, but pure calculation
    # calls below do not touch UI/session state.
    from commerce_engine import calculate_commercial_metrics
    from business_metrics import apply_dashboard_filters, break_even_scenario, revenue_by_period
    from performance_insights import category_profitability
    from audit_exports import build_financial_export, excel_safe_csv
    from full_dataset_engine import explore_dataset
    from investment_engine import evaluate_project
    from forecast_engine import evaluate_cashflow_stress
    checks = []
    base = fixture()
    original = base.copy(deep=True)
    audit, totals = calculate_commercial_metrics(base, 'Sales', 'Cost', 'Discounts', 'Returns')

    def finances():
        for label, expected in [('gross_revenue', 500), ('total_discounts', 15),
                                ('total_returns', 20), ('net_revenue', 465),
                                ('mapped_costs', 280), ('profit_after_mapped_costs', 185)]:
            _near(totals[label], expected, label)
        assert 'net_profit' not in totals, 'Net profit must be gated by assumptions.'
        return 'Gross 500, discounts 15, returns 20, net 465, costs 280, mapped profit 185; net-profit gated'
    checks.append(_run('F5-01', 'Financial mappings', finances))

    def filtered():
        sample = apply_dashboard_filters(base, category_column='Product', categories=['A'],
                                         numeric_column='Sales', numeric_min=30, numeric_max=100)
        assert len(sample) == 2 and sample.Product.eq('A').all()
        _, sums = calculate_commercial_metrics(sample, 'Sales', 'Cost', 'Discounts', 'Returns')
        _near(sums['net_revenue'], 135, 'Filtered net revenue')
        _near(sums['profit_after_mapped_costs'], 65, 'Filtered mapped profit')
        return 'Filtered A: 2 records, revenue 135, profit 65'
    checks.append(_run('F4-01', 'Dashboard filters', filtered))

    def grouped():
        grouped = category_profitability(base, audit, 'Product')
        _near(grouped['Net Revenue'].sum(), 465, 'Grouped revenue')
        _near(grouped['Mapped Costs'].sum(), 280, 'Grouped costs')
        _near(grouped['Profit After Mapped Costs'].sum(), 185, 'Grouped profit')
        assert grouped['Records'].sum() == 4
        return 'Category totals reconcile to mapped financial totals'
    checks.append(_run('F4-02', 'Category profitability', grouped))

    def periods():
        periods, missing = revenue_by_period(base['Date'], audit['Net Revenue'], 'Monthly')
        assert len(periods) == 2 and missing == 0
        assert periods['Period'].tolist() == ['2026-01', '2026-02']
        _near(periods['Revenue'].sum(), 465, 'Period revenue')
        _near(periods.iloc[0]['Revenue'], 270, 'January')
        _near(periods.iloc[1]['Revenue'], 195, 'February')
        return 'January 270 + February 195 = net 465'
    checks.append(_run('F4-03', 'Period analytics', periods))

    def full_search():
        view, exported, m = explore_dataset(base, ['Product', 'Sales'], search_text='A',
                                            preview_limit=1, export_limit=10)
        assert m.matched_rows == 2 and len(view) == 1 and len(exported) == 2
        return 'Search counts entire source before preview cap'
    checks.append(_run('F4-04', 'Data Explorer integration', full_search))

    def clean_export():
        output = build_financial_export(base, audit)
        assert 'BI_Net_Revenue' in output.columns and len(output) == 4
        safe = excel_safe_csv(pd.DataFrame({'Text': ['=2+2', 'plain'], 'Amount': [-4.5, 9]}))
        assert safe.startswith(b'\xef\xbb\xbf') and b"'=2+2" in safe
        assert b'-4.5' in safe
        return 'Collision-safe BI_ headings and spreadsheet-formula text guarded'
    checks.append(_run('F5-02', 'Export safety', clean_export))

    def invalid_finances():
        corrupted = base.copy()
        corrupted.loc[0, 'Cost'] = float('nan')
        try:
            calculate_commercial_metrics(corrupted, 'Sales', 'Cost')
        except ValueError:
            return 'Missing mapped cost correctly blocks calculation'
        raise AssertionError('Missing mapped cost was silently accepted')
    checks.append(_run('F5-03', 'Financial invalid-input guard', invalid_finances))

    def negative_case():
        _, loss = calculate_commercial_metrics(pd.DataFrame({'Sales':[100.0], 'Cost':[120.0]}), 'Sales','Cost')
        _near(loss['net_business_loss'], 20, 'Aggregate loss')
        _near(loss['loss_after_mapped_costs'], 20, 'Row loss')
        return 'Negative mapped profit displayed as loss (not ignored)'
    checks.append(_run('F5-04', 'Loss classification', negative_case))

    def breakeven():
        plan = break_even_scenario(1000, 40, 20)
        assert plan['break_even_units'] == 50
        _near(plan['break_even_revenue'], 2000, 'Break-even revenue')
        assert break_even_scenario(1000, 15, 20)['break_even_units'] is None
        return 'Valid finite break-even and noncontributory case'
    checks.append(_run('F5-05', 'Business planning', breakeven))

    def investment():
        result, _ = evaluate_project(100, [110], 10)
        _near(result['npv'], 0, 'Scenario NPV')
        _near(result['irr_pct'], 10, 'Scenario IRR')
        stress, _ = evaluate_cashflow_stress(100, [110], 10, 20, 20)
        assert stress['Scenario'].tolist() == ['Downside', 'Base', 'Upside']
        return 'Investment mathematics and deterministic scenarios consistent'
    checks.append(_run('F6-01', 'Investment regression', investment))

    def immutable():
        pd.testing.assert_frame_equal(base, original)
        return 'Source business fixture unchanged by calculations and filters'
    checks.append(_run('CROSS-01', 'Source immutability', immutable))

    # These are intentionally not auto-PASS: browser, real client data, deployment.
    checks += [
        Check('F4-UI', 'Phase 4 browser acceptance', 'MANUAL', 'Verify Chart Studio, periods and legacy Dashboard using diverse files.'),
        Check('F5-UI', 'Phase 5 browser acceptance', 'MANUAL', 'Verify financial mapping, currency assumptions, margins, ROI with real accounting data.'),
        Check('SCALE-UI', 'Real application scale', 'MANUAL', 'Benchmark Streamlit Dashboard, Cleaning, Reporting and exports at high row counts.'),
        Check('DEPLOY', 'Production release', 'MANUAL', 'Review access controls, sensitive data, secrets, hosting and deployment.'),
    ]
    return checks
