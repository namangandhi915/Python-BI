from tempfile import TemporaryDirectory
from sector_fixtures import make_sector_fixture, write_demo_csvs

def main():
    for sector in ('Retail','Services','Manufacturing'):
        f=make_sector_fixture(sector,120)
        assert len(f.frame)==120 and f.revenue in f.frame and f.cost in f.frame
        assert f.frame['RecordID'].str.startswith('FAKE-').all()
    with TemporaryDirectory() as d:
        files=write_demo_csvs(d,30)
        assert len(files)==3
    print('PASS: Three sector-specific synthetic CSV fixtures are reproducible')
if __name__=='__main__':main()
