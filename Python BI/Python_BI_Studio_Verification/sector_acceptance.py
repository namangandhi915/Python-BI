"""Cross-sector acceptance with independent arithmetic reconciliation.

Results never contain source records or dataset-specific names outside synthetic labels.
"""
from __future__ import annotations
import math
import pandas as pd
from sector_fixtures import make_sector_fixture
from commerce_engine import calculate_commercial_metrics
from performance_insights import category_profitability
from business_metrics import apply_dashboard_filters, revenue_by_period
from scalable_analytics import category_chart_data, time_chart_data
from audit_exports import build_financial_export, excel_safe_csv
from report_engine import build_executive_report


def _close(a, b, name):
    if not math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=.01):
        raise AssertionError(f'{name} did not reconcile.')


def check_one_sector(name: str, rows: int = 120) -> dict:
    case = make_sector_fixture(name, rows)
    data = case.frame
    original = data.copy(deep=True)
    audit, totals = calculate_commercial_metrics(
        data, case.revenue, case.cost, case.discount, case.returns, case.operating, case.taxes,
        complete_costs=True,
    )
    gross = data[case.revenue].sum()
    net = gross - data[case.discount].sum() - data[case.returns].sum()
    costs = data[[case.cost,case.operating,case.taxes]].sum().sum()
    _close(totals['gross_revenue'], gross, 'gross revenue')
    _close(totals['net_revenue'], net, 'net revenue')
    _close(totals['mapped_costs'], costs, 'mapped costs')
    _close(totals['net_profit'], net - costs, 'synthetic fully-mapped profit')
    grouped = category_profitability(data,audit,case.category)
    _close(grouped['Net Revenue'].sum(),net,'category revenue')
    _close(grouped['Profit After Mapped Costs'].sum(),net-costs,'category profit')
    periods, missing = revenue_by_period(data[case.date],audit['Net Revenue'],'Monthly')
    assert missing == 0 and len(periods) >= 3
    _close(periods['Revenue'].sum(),net,'period revenue')
    chosen = apply_dashboard_filters(data,category_column=case.category,categories=[str(data[case.category].iloc[0])])
    assert 0 < len(chosen) < len(data)
    view = build_financial_export(data,audit)
    assert len(view)==rows and 'BI_Net_Revenue' in view.columns
    assert excel_safe_csv(view).startswith(b'\xef\xbb\xbf')
    bar, bmeta = category_chart_data(data,audit,case.category,'Calculated: Net Revenue',top_n=12)
    _close(bar['Value'].sum(),net,'category chart')
    line, lmeta = time_chart_data(data,audit,case.date,'Calculated: Net Revenue','Monthly')
    _close(line['Value'].sum(),net,'line chart')
    document=build_executive_report(data,audit,totals,dataset_name='Fictional Sector Fixture',
                                   category=case.category,date_column=case.date,period='Monthly',
                                   field_mapping={'revenue':case.revenue,'cost':case.cost},
                                   filter_notes='No filters — fictional dataset')
    assert b'<html' in document['html'].lower()
    assert len(document['summary'])>0
    invalid=data.copy()
    invalid.loc[0,case.cost]=float('nan')
    try:
        calculate_commercial_metrics(invalid,case.revenue,case.cost)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid financial input should be rejected')
    pd.testing.assert_frame_equal(data, original)
    return {'sector': name,'rows':rows,'gross_revenue_reconciled':True,
            'net_revenue_reconciled':True,'mapped_costs_reconciled':True,
            'synthetic_net_profit_reconciled':True,'category_reconciled':True,
            'time_reconciled':True,'charts_reconciled':True,
            'report_generated':True,'invalid_input_rejected':True,
            'source_unchanged':True, 'status':'PASS'}


def run_sector_acceptance(rows: int = 120) -> list[dict]:
    return [check_one_sector(s,rows) for s in ('Retail','Services','Manufacturing')]
