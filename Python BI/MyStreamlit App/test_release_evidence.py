from tempfile import TemporaryDirectory
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from release_evidence import build_report, evidence_zip, html_report
from release_cli import main


def test():
    with TemporaryDirectory() as tmp:
        root=Path(tmp)
        (root/'.streamlit').mkdir()
        (root/'.streamlit'/'config.toml').write_text('[theme]\nbase="light"\n')
        r=build_report(root)
        assert r['gate']=='BLOCKED_FOR_PUBLIC_DEPLOYMENT'
        assert r['counts']['BLOCKED']>=3
        html=html_report(r)
        assert 'Release Readiness' in html and '<table>' in html
        pack=evidence_zip(r)
        with ZipFile(BytesIO(pack)) as z:
            assert set(z.namelist())=={'release_readiness.json','release_readiness.html','README.txt'}
            assert 'stored_datasets' in z.read('release_readiness.json').decode()
        dest=root/'evidence'
        assert main(['--output',str(dest)])==0
        assert (dest/'release_readiness.json').exists() and (dest/'release_readiness_pack.zip').exists()
    print('PASS: Conservative release gate, minimal ZIP evidence, HTML/JSON and CLI')

if __name__=='__main__':test()
