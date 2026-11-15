"""Measured multi-module data pipeline benchmark (CLI, not browser-level certification)."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from pathlib import Path
from time import perf_counter
import gc
import json
import numpy as np
import pandas as pd

from benchmark_explorer import make_synthetic
from full_dataset_engine import explore_dataset
from business_metrics import apply_dashboard_filters,revenue_by_period
from performance_insights import category_profitability
from data_readiness import dataset_profile

MAX_ROWS=500_000


def benchmark_workflow(rows:int=10_000, *, existing_csv:str|None=None)->dict:
    """Generate/read a synthetic dataset, run UI underlying modules with measured timings.

    No Streamlit browser, widgets, charts, or complete reporting ZIP are benchmarked.
    Never calls app.py or writes any datasets to Dataset Library.
    """
    if type(rows) is not int or not 100<=rows<=MAX_ROWS:
        raise ValueError(f'Rows must be integer between 100 and {MAX_ROWS:,}.')
    events={}
    start=perf_counter()
    if existing_csv:
        frame=pd.read_csv(existing_csv)
        if len(frame)>MAX_ROWS:
            raise ValueError('CSV exceeds maximum benchmark rows')
        if len(frame)!=rows:
            raise ValueError(f'CSV row count {len(frame)} does not match --rows {rows}')
        mode='CSV read into Pandas'
    else:
        frame=make_synthetic(rows)
        mode='Deterministic synthetic generator'
    events['load_or_generate_seconds']=round(perf_counter()-start,5)
    source_shape=list(frame.shape)
    frame_mem=round(float(frame.memory_usage(index=True,deep=True).sum())/1048576,3)

    start=perf_counter()
    # The last-row sentinel tests full-scan search through ALL fields, matching once.
    sentinel=f'SPECIAL-ROW-{rows-1:09d}'
    preview,export,meta=explore_dataset(frame,frame.columns.tolist(),search_text=sentinel,
                                        preview_limit=10,export_limit=100)
    events['search_all_columns_seconds']=round(perf_counter()-start,5)
    assert meta.matched_rows==1 and len(preview)==1 and len(export)==1
    assert sentinel in preview.astype('string').to_string(index=False)

    start=perf_counter()
    overview,columns,sample=dataset_profile(frame,sample_limit=min(rows,5000),exact_missing_scan=False)
    assert overview['source_rows']==rows and len(columns)==frame.shape[1]
    events['sampled_readiness_seconds']=round(perf_counter()-start,5)

    # Benchmark filters and mapped-cost financial engine on SAME source rows.
    numeric_col=next((c for c in ('Sales','Total Cost') if c in frame.columns),None)
    if not numeric_col or 'Total Cost' not in frame.columns:
        raise AssertionError('Synthetic benchmark schema unexpectedly changed.')
    start=perf_counter()
    selected=apply_dashboard_filters(frame,numeric_column='Sales',numeric_min=0,numeric_max=1e15)
    events['dashboard_filter_seconds']=round(perf_counter()-start,5)
    from commerce_engine import calculate_commercial_metrics
    start=perf_counter()
    calculations,totals=calculate_commercial_metrics(selected,'Sales','Total Cost')
    events['mapped_finance_seconds']=round(perf_counter()-start,5)
    assert np.isclose(totals['profit_after_mapped_costs'],totals['net_revenue']-totals['mapped_costs'])

    start=perf_counter()
    grouped=category_profitability(selected,calculations,'Product')
    events['category_reconciliation_seconds']=round(perf_counter()-start,5)
    assert np.isclose(grouped['Net Revenue'].sum(),totals['net_revenue'])
    assert np.isclose(grouped['Mapped Costs'].sum(),totals['mapped_costs'])

    start=perf_counter()
    periods,invalid=revenue_by_period(selected['Date'],calculations['Net Revenue'],'Monthly')
    events['period_reconciliation_seconds']=round(perf_counter()-start,5)
    assert np.isclose(periods['Revenue'].sum(),totals['net_revenue'])
    return {'scope':'Real underlying Python BI Studio module chain; NOT the Streamlit browser or full report generation',
            'source':mode,'rows':rows,'columns':source_shape[1],
            'dataframe_memory_mib':frame_mem,'sentinel_found_once':True,
            'sample_quality_rows':overview['sample_rows'],'financial_reconciled':True,
            'category_reconciled':True,'period_reconciled':True,
            'period_invalid_dates':invalid,'timings_seconds':events,
            'full_app_certified':False}


def save_benchmark(result:dict,target:Path)->None:
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
