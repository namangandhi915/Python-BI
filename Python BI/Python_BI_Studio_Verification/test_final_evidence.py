from tempfile import TemporaryDirectory
from pathlib import Path
import run_final_acceptance as m
with TemporaryDirectory() as folder:
    original=m.OUT
    try:
        m.OUT=Path(folder)/'results'
        result=m.run(10_000)
        assert result['release_status']=='AUTOMATED_PASS__MANUAL_ACCEPTANCE_PENDING'
        assert result['pass_count']>=30 and result['fail_count']==0
        assert result['actual_browser_passed'] is False
        assert result['public_hosting']=='NOT_AUTHORIZED'
        evidence=m.OUT/'FINAL_ACCEPTANCE_EVIDENCE.zip'
        assert evidence.is_file() and evidence.stat().st_size>1000
        import zipfile
        with zipfile.ZipFile(evidence) as package:
            names=package.namelist()
            assert 'FINAL_ACCEPTANCE_REPORT.html' in names
            assert 'FINAL_ACCEPTANCE_REPORT.json' in names
    finally:m.OUT=original
print('PASS: Local acceptance evidence, synthetic-only data and manual/approval gates remain pending')
