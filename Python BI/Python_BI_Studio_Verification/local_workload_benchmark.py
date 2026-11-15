"""Measured local Python BI module workflow, including chart preparation and report construction.

This is NOT a full browser benchmark. Real Streamlit interactions still need a manual test.
No user files, Dataset Library, network, or public server are accessed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from time import perf_counter
import math
from benchmark_explorer import make_synthetic
from full_dataset_engine import explore_dataset
from commerce_engine import calculate_commercial_metrics
from business_metrics import apply_dashboard_filters
from quality_engine import quality_overview
from portfolio_analytics import build_category_concentration
from scalable_analytics import category_chart_data, time_chart_data
from report_engine import build_executive_report
from audit_exports import excel_safe_csv


def run_workload(rows: int = 10_000) -> dict:
    if type(rows) is not int or not 100 <= rows <= 500_000:
        raise ValueError('Use 100 to 500,000 synthetic rows.')
    steps={}
    start=perf_counter(); source=make_synthetic(rows)
    steps['source_generation_sec']=round(perf_counter()-start,4)
    mem=round(float(source.memory_usage(index=True, deep=True).sum())/1048576,2)
    sentinel=f'SPECIAL-ROW-{rows-1:09d}'
    start=perf_counter(); preview,_,meta=explore_dataset(source,source.columns.tolist(),search_text=sentinel,preview_limit=10)
    steps['full_dataset_search_sec']=round(perf_counter()-start,4)
    assert meta.matched_rows==1 and len(preview)==1
    start=perf_counter(); health=quality_overview(source)
    steps['quality_scan_sec']=round(perf_counter()-start,4)
    assert health['rows']==rows
    start=perf_counter(); filtered=apply_dashboard_filters(source,numeric_column='Sales',numeric_min=0,numeric_max=1e15)
    steps['dashboard_filter_sec']=round(perf_counter()-start,4)
    start=perf_counter(); audit, totals=calculate_commercial_metrics(filtered,'Sales','Total Cost')
    steps['financial_calculations_sec']=round(perf_counter()-start,4)
    assert math.isclose(totals['profit_after_mapped_costs'],totals['net_revenue']-totals['mapped_costs'],abs_tol=.01)
    start=perf_counter(); concentration=build_category_concentration(filtered,audit,totals,'Product')
    steps['category_concentration_sec']=round(perf_counter()-start,4)
    assert math.isclose(concentration['groups']['Net Revenue'].sum(),totals['net_revenue'],abs_tol=.01)
    start=perf_counter(); bar,_=category_chart_data(filtered,audit,'Product','Calculated: Net Revenue')
    line,_=time_chart_data(filtered,audit,'Date','Calculated: Net Revenue','Monthly')
    steps['chart_series_preparation_sec']=round(perf_counter()-start,4)
    assert math.isclose(bar['Value'].sum(),totals['net_revenue'],abs_tol=.01)
    assert math.isclose(line['Value'].sum(),totals['net_revenue'],abs_tol=.01)
    start=perf_counter(); report=build_executive_report(
        filtered,audit,totals,dataset_name='Synthetic performance case',
        category='Product',date_column='Date',period='Monthly',
        field_mapping={'Revenue':'Sales','Cost':'Total Cost'},filter_notes='Synthetic, unfiltered')
    steps['executive_html_generation_sec']=round(perf_counter()-start,4)
    assert len(report['html'])>500
    start=perf_counter(); output=excel_safe_csv(audit.head(200))
    steps['bounded_csv_export_sec']=round(perf_counter()-start,4)
    assert output.startswith(b'\xef\xbb\xbf')
    return {'rows':rows,'columns':source.shape[1],'source_memory_mib':mem,
            'steps_sec':steps,'all_module_reconciliations':True,
            'includes_html_report_generation':True,
            'includes_chart_series_but_not_browser_render':True,
            'streamlit_full_ui_certified':False,
            'scope':'Local synthetic full module-chain performance; NOT a Streamlit user-interface load test',
            'status':'PASS'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows',type=int,default=10000)
    p.add_argument('--output',default='professor_results/workload.json')
    args=p.parse_args(argv)
    result=run_workload(args.rows)
    dest=Path(args.output); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS: Local module-chain workload', args.rows,'rows; chart data and HTML report included.')
    print('Browser rendering and public hosting: NOT PERFORMED.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
