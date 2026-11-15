"""Dataset quality contract tests on deliberately duplicated/missing rows."""
import pandas as pd
from assurance_contracts import inspect_dataset, schema_fingerprint, readiness_notes

def main():
    data=pd.DataFrame({'Sales':[10,10,None,5], 'Product':['A','A',None,'B']})
    before=data.copy(deep=True)
    sample, table=inspect_dataset(data,sample_size=100,exact=False)
    assert sample['rows']==4 and sample['columns']==2 and sample['sample_rows']==4
    assert sample['scope']=='sample_only' and sample['checked_missing_cells']==2
    exact, fields=inspect_dataset(data,sample_size=2,exact=True)
    assert exact['checked_duplicate_rows']==1 and exact['checked_missing_cells']==2
    assert fields['Checked scope'].eq('All source rows').all()
    assert len(schema_fingerprint(data))==16
    assert inspect_dataset(None)[0]['status']=='no_active_dataset'
    try: inspect_dataset(data,sample_size=0)
    except ValueError: pass
    else: raise AssertionError('Invalid sample size accepted')
    try: inspect_dataset(data.rename(columns={'Product':'Sales'}))
    except ValueError:pass
    else: raise AssertionError('Duplicate names accepted')
    pd.testing.assert_frame_equal(data,before)
    print('PASS: Deterministic quality scope, exact counts, duplicate labels, source immutability')
if __name__=='__main__':main()
