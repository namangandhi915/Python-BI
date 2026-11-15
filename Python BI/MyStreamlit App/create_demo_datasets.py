"""Create three obviously fictional local CSVs for professor demonstration."""
from pathlib import Path
import argparse
from sector_fixtures import write_demo_csvs

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rows',type=int,default=120)
    ap.add_argument('--output-dir',default='demo_artifacts')
    args=ap.parse_args(argv)
    root=Path(__file__).resolve().parent
    folder=(root/args.output_dir)
    if folder.resolve().parent!=root.resolve():
        raise ValueError('Demo output folder must be directly inside this local project.')
    paths=write_demo_csvs(folder,args.rows)
    print('PASS: Created',len(paths),'FAKE datasets. They are not saved to Dataset Library automatically.')
    for p in paths:print(' ',Path(p).name)
    return 0
if __name__=='__main__':raise SystemExit(main())
