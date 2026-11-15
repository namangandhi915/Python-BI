"""Non-destructive local recovery, dataset path and export-safety tests.

All files created for this suite live in temporary directories; no user's
stored_datasets directory, saved active dataset, or real workbook is modified.
"""
from __future__ import annotations
from tempfile import TemporaryDirectory
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json
import pandas as pd
from local_file_guard import safe_stored_path, validate_upload
from audit_exports import excel_safe_csv
from report_engine import build_executive_report
from commerce_engine import calculate_commercial_metrics


class FakeUpload:
    def __init__(self, name: str, raw: bytes):
        self.name=name;self.raw=raw;self.size=len(raw)
    def getvalue(self):return self.raw


def run_recovery_checks() -> list[dict]:
    results=[]
    def run(key, title, fn):
        try:
            detail=fn()
            results.append({'id':key,'title':title,'status':'PASS','detail':str(detail or 'Verified')})
        except Exception as err:
            results.append({'id':key,'title':title,'status':'FAIL','detail':f'{type(err).__name__}: {err}'})
    def reject(fn):
        try:fn()
        except (OSError,ValueError,FileNotFoundError):return
        raise AssertionError('Unsafe path/input was accepted')
    def private_library():
        with TemporaryDirectory() as tmp:
            library=Path(tmp)/'stored_datasets';library.mkdir()
            data=b'Revenue,Cost\n100,40\n'
            named='fixture_001.csv'; saved=safe_stored_path(library,named)
            saved.write_bytes(data)
            metadata={'stored_name':named,'hash':sha256(data).hexdigest()}
            # Simulate the same SHA-256 check used for app.py restore.
            assert sha256(safe_stored_path(library,metadata['stored_name'],must_exist=True).read_bytes()).hexdigest()==metadata['hash']
            saved.write_bytes(data+b'200,120\n')
            assert sha256(saved.read_bytes()).hexdigest()!=metadata['hash']
            reject(lambda:safe_stored_path(library,'../outside.csv',must_exist=True))
            reject(lambda:safe_stored_path(library,'C:\\outside.csv'))
            reject(lambda:safe_stored_path(library,'notfound.csv',must_exist=True))
        return 'Temporary library tampering detected; traversal and missing saved files blocked'
    run('G4-01','Temporary library recovery/integrity verification',private_library)
    def valid_csv():
        info=validate_upload(FakeUpload('SYNTHETIC.csv',b'Gross,Cost\n10,5\n'))
        assert info['extension']=='.csv' and info['sha256']==sha256(b'Gross,Cost\n10,5\n').hexdigest()
        return 'Local CSV passed validation without uploading or changing any saved dataset'
    run('G4-02','Local fake-CSV upload validation',valid_csv)
    def invalid_uploads():
        reject(lambda:validate_upload(FakeUpload('../outside.csv',b'a,b\n1,2')))
        reject(lambda:validate_upload(FakeUpload('payload.exe',b'a,b\n1,2')))
        reject(lambda:validate_upload(FakeUpload('trick.csv',b'PK\x03\x04fake archive')))
        reject(lambda:validate_upload(FakeUpload('blank.csv',b'')))
        return 'Traversal, unsupported extension, archive-masquerading and empty data blocked'
    run('G4-03','Unsafe dataset input rejection',invalid_uploads)
    def formula_export():
        src=pd.DataFrame({'Text':['+EVIL()','  =1+1','-CMD()', '@SUM(1,2)'],
                          'Revenue':[1.,-2.,0.,3.]})
        original=src.copy(deep=True)
        csv=excel_safe_csv(src)
        assert csv.startswith(b'\xef\xbb\xbf')
        for marker in [b"'+EVIL",b"'  =1+1",b"'-CMD",b"'@SUM"]: assert marker in csv, marker
        assert b'-2.0' in csv
        pd.testing.assert_frame_equal(src,original)
        return 'Formula-like text guarded; negative numeric amount stays numeric; source untouched'
    run('G4-04','Spreadsheet export hardening',formula_export)
    def report_escape():
        source=pd.DataFrame({'Category':['<script>alert(1)</script>'], 'Gross':[40.], 'Cost':[10.]})
        audit,totals=calculate_commercial_metrics(source,'Gross','Cost')
        result=build_executive_report(source,audit,totals,dataset_name='<private>&test',
                                      category='Category',date_column=None,period='Monthly',
                                      field_mapping={'source':'<script>alert(1)</script>'},
                                      filter_notes='<x>',currency_label='Unspecified')
        html=result['html'].decode()
        assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html
        assert '<private>' not in html and '&lt;private&gt;' in html
        return 'User-provided category, field map and dataset labels are HTML-escaped'
    run('G4-05','HTML report escaping',report_escape)
    def invalid_report():
        source=pd.DataFrame({'Gross':[100.], 'Cost':[10.]})
        audit,totals=calculate_commercial_metrics(source,'Gross','Cost')
        mismatch=dict(totals);mismatch['gross_revenue']=200.
        reject(lambda:build_executive_report(source,audit,mismatch,dataset_name='SYNTHETIC',
                              category=None,date_column=None,period='Monthly',field_mapping={},filter_notes='test'))
        return 'Report generator refuses mismatched audit totals'
    run('G4-06','Out-of-balance report rejection',invalid_report)
    return results


if __name__=='__main__':
    out=run_recovery_checks()
    for item in out: print(item['status']+': '+item['id']+' — '+item['title'])
    print('TOTAL:',sum(x['status']=='PASS' for x in out),'passed,',sum(x['status']=='FAIL' for x in out),'failed')
    raise SystemExit(0 if all(x['status']=='PASS' for x in out) else 1)
