"""Create SYNTHETIC ONLY 14-column scale CSVs for local Streamlit browser tests.

Never activates or changes the user's stored datasets. Outputs to acceptance_artifacts.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from benchmark_explorer import make_synthetic

def generate(rows:int,folder:Path=Path('acceptance_artifacts')) -> str:
    if rows not in (10_000,100_000,500_000):
        raise ValueError('Only 10000, 100000 or 500000 synthetic rows are supported.')
    target=Path(folder);target.mkdir(parents=True,exist_ok=True)
    data=make_synthetic(rows)
    if data.shape[1]!=14: raise AssertionError('Expected 14 columns')
    path=target/f'FAKE_PERFORMANCE_{rows}.csv'
    data.to_csv(path,index=False)
    print(f'SYNTHETIC ONLY: {path} | {rows:,} records | {path.stat().st_size/1048576:.1f} MiB')
    return str(path)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows',type=int,nargs='+',choices=[10000,100000,500000],default=[10000,100000])
    args=p.parse_args()
    for count in args.rows: generate(count)
