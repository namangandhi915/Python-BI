"""Run: python scripts/run_final_gate_tests.py — does not launch Streamlit."""
import sys
import types
from pathlib import Path
import pandas as pd

# Allows calculation-logic tests in a Python environment without Streamlit running.
if 'streamlit' not in sys.modules:
    try:
        import streamlit
    except ImportError:
        sys.modules['streamlit'] = types.SimpleNamespace()

from commerce_engine import calculate_commercial_metrics
from quality_engine import quality_overview, quality_table, missing_records

frame = pd.DataFrame({
    'Sales':[100.0,80.0,20.0],
    'Total Cost':[40.0,90.0,10.0],
    'Discounts':[10.0,0.0,0.0],
    'City':['Delhi',None,'Mumbai'],
})
calc, m = calculate_commercial_metrics(frame,'Sales','Total Cost','Discounts')
assert round(m['gross_revenue'],2) == 200
assert round(m['net_revenue'],2) == 190
assert round(m['mapped_costs'],2) == 140
assert round(m['profit_after_mapped_costs'],2) == 50
assert round(m['loss_after_mapped_costs'],2) == 10
assert round(m['net_business_loss'],2) == 0
assert 'net_profit' not in m
assert quality_overview(frame)['rows_with_missing'] == 1
assert len(missing_records(frame,'City')) == 1
assert quality_table(frame).loc[quality_table(frame)['Column']=='City','Missing %'].iloc[0] > 0
try:
    calculate_commercial_metrics(frame.assign(Sales=[100,None,20]),'Sales','Total Cost')
    raise AssertionError('Should reject missing financial values')
except ValueError:
    pass
try:
    calculate_commercial_metrics(frame,'Sales','Sales')
    raise AssertionError('Should reject duplicated mappings')
except ValueError:
    pass

# Optional integration test against user's bundled workbook when available.
workbook = Path(__file__).resolve().parents[1]/'data'/'business'/'Python_BI_Complete_Business_Dataset.xlsx'
if workbook.exists():
    real_df=pd.read_excel(workbook,sheet_name='Business Data')
    _,real=calculate_commercial_metrics(real_df,'Sales','Total Cost')
    assert abs(real['profit_after_mapped_costs']-(real_df['Sales']-real_df['Total Cost']).sum())<1e-6
    print('Bundled workbook: validated')
print('PASS: Commercial calculations, loss distinctions, invalid inputs, quality inspection')
