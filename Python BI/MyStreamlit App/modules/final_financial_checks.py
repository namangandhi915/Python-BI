"""Independent arithmetic and edge-case acceptance for Phases 4 and 5.

Synthetic fixtures only; never reads private datasets or calls external services.
Results contain only check identifiers and pass/fail messages, not records.
"""
from __future__ import annotations
from math import isclose
from collections.abc import Callable
import pandas as pd
from commerce_engine import calculate_commercial_metrics, NONE
from business_metrics import apply_dashboard_filters, revenue_by_period, break_even_scenario
from performance_insights import category_profitability
from audit_exports import build_financial_export, excel_safe_csv
from report_engine import build_executive_report
from sector_acceptance import check_one_sector
from schema_aware_dashboard import assess_legacy


def close(a, b, label):
    assert a is not None and isclose(float(a),float(b),abs_tol=0.01,rel_tol=1e-10), (label,a,b)


def expect_error(fn: Callable, message: str):
    try: fn()
    except (ValueError, TypeError): return
    raise AssertionError(message)


def case() -> pd.DataFrame:
    return pd.DataFrame({
        'Category':['A',None,'A','B'],
        'Date':['2025-12-12','invalid','2026-01-05','2026-02-10'],
        'Gross':[100.,0.,-20.,80.],
        'Cost':[40.,0.,0.,90.],
        'Discount':[5.,0.,0.,0.],
        'Returns':[0.,0.,0.,10.],
        'Operations':[3.,0.,0.,7.],
        'Taxes':[2.,0.,0.,3.],
    })


def financial_edge_suite() -> list[dict]:
    tests=[]
    def record(key, title, fn):
        try:
            detail=fn()
            tests.append({'id':key,'title':title,'status':'PASS','detail':str(detail or 'Verified')})
        except Exception as err:
            tests.append({'id':key,'title':title,'status':'FAIL',
                          'detail':f'{type(err).__name__}: {err}'})
    frame=case(); original=frame.copy(deep=True)
    audit, totals=calculate_commercial_metrics(frame,'Gross','Cost','Discount','Returns','Operations','Taxes',complete_costs=True)

    def independent_reconciliation():
        # Independent row arithmetic, without using the totals being tested.
        gross=sum([100,0,-20,80]); discount=5; returns=10
        expenses=sum([40,0,0,90])+sum([3,0,0,7])+sum([2,0,0,3])
        for key,val in [('gross_revenue',gross),('total_discounts',discount),
                        ('total_returns',returns),('net_revenue',gross-discount-returns),
                        ('mapped_costs',expenses),('profit_after_mapped_costs',gross-discount-returns-expenses),
                        ('net_profit',gross-discount-returns-expenses)]:close(totals[key],val,key)
        close(float(audit['Net Revenue'].sum()),gross-discount-returns,'audited Net Revenue')
        return 'Gross 160; discounts 5; returns 10; net 145; mapped costs 145; net 0'
    record('F5-01','Independent revenue/cost/discount/returns/tax reconciliation',independent_reconciliation)

    def row_losses():
        individual=[100-5-40-3-2,0,-20,80-10-90-7-3]
        close(totals['loss_after_mapped_costs'],sum(-x for x in individual if x<0),'row losses')
        close(totals['net_business_loss'],0,'net business loss')
        return 'Row-level losses deliberately distinguished from net business loss'
    record('F5-02','Loss vs cumulative row losses',row_losses)

    record('F5-03','Zero net revenue yields undefined profit margin',
           lambda: (lambda t: t['profit_margin_pct'] is None or (_ for _ in ()).throw(AssertionError('margin not undefined')))(
               calculate_commercial_metrics(pd.DataFrame({'Gross':[0.], 'Cost':[5.]}),'Gross','Cost')[1]))
    record('F5-04','Missing cost cannot silently discard operating expenses',
           lambda: expect_error(lambda: calculate_commercial_metrics(frame,'Gross',operating_expenses='Operations'),
                                'Operating expenses without mapped cost did not raise'))
    record('F5-05','Taxes without cost are not silently ignored',
           lambda: expect_error(lambda: calculate_commercial_metrics(frame,'Gross',taxes='Taxes'),
                                'Tax without mapped cost did not raise'))
    record('F5-06','Duplicate numeric column role prohibited',
           lambda: expect_error(lambda: calculate_commercial_metrics(frame,'Gross','Cost',discount='Cost'),
                                'Overlapping field mapping was accepted'))
    record('F5-07','Invalid financial null blocks figures',
           lambda: expect_error(lambda: calculate_commercial_metrics(frame.assign(Cost=[float('nan'),0,0,90]),'Gross','Cost'),
                                'Missing cost accepted'))
    record('F5-08','Infinite monetary value rejected',
           lambda: expect_error(lambda: calculate_commercial_metrics(frame.assign(Gross=[float('inf'),0,-20,80]),'Gross','Cost'),
                                'Infinite revenue accepted'))
    record('F5-09','Duplicate column labels rejected',
           lambda: expect_error(lambda: calculate_commercial_metrics(pd.DataFrame([[1,2]],columns=['Gross','Gross']),'Gross'),
                                'Duplicate labels accepted'))
    def no_net_claim():
        _,m=calculate_commercial_metrics(frame,'Gross','Cost')
        assert 'net_profit' not in m and 'roi_pct' not in m
        return 'Profit after mapped costs is not labelled accounting net profit'
    record('F5-10','Net profit requires explicit complete-cost confirmation',no_net_claim)
    def capital_rules():
        data=pd.DataFrame({'Gross':[100.,100.],'Cost':[30.,40.],'Capital':[50.,50.]})
        _,m=calculate_commercial_metrics(data,'Gross','Cost',invested_capital='Capital',complete_costs=True)
        assert 'roi_pct' not in m
        _,yes=calculate_commercial_metrics(data,'Gross','Cost',invested_capital='Capital',complete_costs=True,capital_is_row_additive=True)
        close(yes['roi_pct'],130,'ROI')
        return 'ROI 130% only with confirmed additive capital'
    record('F5-11','ROI opt-in additive-capital treatment',capital_rules)
    def filters():
        empty=apply_dashboard_filters(frame,category_column='Category',categories=[])
        assert empty.empty
        subset=apply_dashboard_filters(frame,numeric_column='Gross',numeric_min=-20,numeric_max=0)
        assert len(subset)==2
        return 'Explicit empty selection returns zero; negative and zero values preserved'
    record('F4-01','Dashboard empty and negative numeric filters',filters)
    def dates():
        periods,omitted=revenue_by_period(frame['Date'],audit['Net Revenue'])
        assert omitted==1 and len(periods)==3
        close(periods['Revenue'].sum(),totals['net_revenue'],'dated totals')  # missing date row has net 0
        assert periods.iloc[0]['Period']=='2025-12'
        return 'Multi-year grouping correct; 1 invalid date excluded from trend only'
    record('F4-02','Date parsing and multi-year period integrity',dates)
    def category():
        grouped=category_profitability(frame,audit,'Category')
        close(grouped['Net Revenue'].sum(),145,'category revenues')
        close(grouped['Profit After Mapped Costs'].sum(),0,'category profit')
        assert grouped['Records'].sum()==4
        return 'Missing category retained and group totals reconcile'
    record('F4-03','Null category and aggregation reconciliation',category)
    def report():
        output=build_executive_report(frame,audit,totals,dataset_name='SYNTHETIC ONLY',
            category='Category',date_column='Date',period='Monthly',
            field_mapping={'gross revenue':'Gross'},filter_notes='Synthetic', currency_label='Unspecified')
        close(output['summary'].loc[output['summary']['Metric']=='Net Revenue','Value'].iloc[0],145,'report net')
        close(output['categories']['Net Revenue'].sum(),145,'report groups')
        assert output['missing_date_rows']==1
        assert b'SYNTHETIC ONLY' in output['html']
        return 'KPI, category, trend and HTML report agree on the synthetic fixture'
    record('F7-01','Report-to-source totals and missing-date disclosure',report)
    def incorrect_report_blocked():
        wrong=dict(totals);wrong['net_revenue']=999
        expect_error(lambda:build_executive_report(frame,audit,wrong,dataset_name='Synthetic',
                  category='Category',date_column='Date',period='Monthly',
                  field_mapping={},filter_notes='Synthetic'), 'Mismatched report totals accepted')
        return 'Incorrect report totals stop report generation'
    record('F7-02','Tampered report totals fail closed',incorrect_report_blocked)
    def safe_csv():
        exported=excel_safe_csv(pd.DataFrame({'Text':['=HYPERLINK("https://test")','  @SUM(1,2)','plain'],
                                               'Amount':[-5.0,0.0,5.0]}))
        assert b"'=HYPERLINK" in exported and b"'  @SUM" in exported and b'-5.0' in exported
        assert len(build_financial_export(frame,audit))==len(frame)
        return 'Formula-like text escaped and negative numeric amounts preserved'
    record('F7-03','Spreadsheet export formula safety and record alignment',safe_csv)
    record('F4-04','Original source DataFrame unchanged',
           lambda:pd.testing.assert_frame_equal(frame,original))
    for sector in ('Retail','Services','Manufacturing'):
        def sector_test(name=sector):
            report=check_one_sector(name,120)
            assert report['status']=='PASS'
            return f'{name}: independent sector finance/dashboard/report checks passed'
        record(f'F45-SECTOR-{sector.upper()}',f'{sector} schema acceptance',sector_test)
    def legacy_compatibility():
        base=pd.DataFrame({'Sales':[100.,200.],'Total Cost':[60.,100.],'Profit':[40.,100.],
             'Profit Margin (%)':[40.,50.],'Quantity':[2,4],
             'Product':['A','B'],'Region':['N','S'],'City':['X','Y'],
             'Date':pd.to_datetime(['2026-01-01','2026-02-01']),
             'ProductID':['P1','P2'],'CustomerID':['C1','C2']})
        assert assess_legacy(base).compatible
        assert not assess_legacy(base.assign(Profit=[99.,100.])).compatible
        assert not assess_legacy(base.assign(**{'Profit Margin (%)':[99.,50.]})).compatible
        assert not assess_legacy(base.drop(columns=['ProductID'])).compatible
        assert not assess_legacy(base.assign(Sales=[float('nan'),200.])).compatible
        assert not assess_legacy(base, max_rows=1).compatible
        return 'Correct legacy passes; inconsistent, missing, nonfinite or oversize legacy is redirected'
    record('F4-05','Legacy compatibility and reconciliation gate',legacy_compatibility)
    record('F5-12','Break-even and noncontributing-price handling',
           lambda: (close(break_even_scenario(500,20,10)['break_even_revenue'],1000,'break-even'),
                    break_even_scenario(500,10,20)['break_even_units'] is None or (_ for _ in ()).throw(AssertionError('finite break-even wrongly returned'))))
    return tests


if __name__=='__main__':
    results=financial_edge_suite()
    for r in results:print(r['status']+': '+r['id']+' — '+r['title'])
    print('TOTAL:',sum(x['status']=='PASS' for x in results),'passed,',sum(x['status']=='FAIL' for x in results),'failed')
    raise SystemExit(0 if all(x['status']=='PASS' for x in results) else 1)
