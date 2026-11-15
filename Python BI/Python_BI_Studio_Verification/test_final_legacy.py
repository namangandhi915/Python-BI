from pathlib import Path
import pandas as pd
from schema_aware_dashboard import assess_legacy
src=pd.DataFrame({'Sales':[100.], 'Total Cost':[70.], 'Profit':[30.], 'Profit Margin (%)':[30.],
                  'Quantity':[1],'Product':['A'],'Region':['R'],'City':['C'],
                  'Date':[pd.Timestamp('2026-01-01')], 'ProductID':['P1'], 'CustomerID':['C1']})
assert assess_legacy(src).compatible
assert not assess_legacy(src.rename(columns={'Product':'Service'})).compatible
assert not assess_legacy(src.assign(Profit=[999.])).compatible
assert not assess_legacy(src.assign(Sales=[float('nan')])).compatible
assert not assess_legacy(src, max_rows=0).compatible
app=(Path(__file__).resolve().parent/'app.py').read_text(encoding='utf-8')
assert 'legacy_assessment = assess_legacy(' in app
assert 'render_safe_details' in app
assert 'render_executive_dashboard = instrument("Executive Dashboard"' in app
assert 'professor_review_ui' not in app
print('PASS: Legacy schema guard, finance reconciler, safe fallback and existing Dashboard wiring')
