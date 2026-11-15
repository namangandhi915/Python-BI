"""Ensure audit bundles are parseable, escaped and do not contain raw data."""
from io import BytesIO
from zipfile import ZipFile
import json
from assurance_reports import report_document, render_html, bundle_audit

def main():
    checks=[{'id':'x<','area':'dataset','status':'PASS','detail':'<script>alert(1)</script>'},
            {'id':'manual','area':'UI','status':'MANUAL','detail':'Browser review pending'}]
    report=report_document(checks,scope='Phases 4 and 5')
    assert report['counts']['PASS']==1 and report['counts']['MANUAL']==1
    assert report['release_gate']=='REVIEW_REQUIRED'
    html=render_html(report)
    assert '<script>' not in html and '&lt;script&gt;' in html
    blob=bundle_audit(report)
    with ZipFile(BytesIO(blob)) as archive:
        assert set(archive.namelist())=={'acceptance_summary.json','acceptance_summary.html','README.txt'}
        parsed=json.loads(archive.read('acceptance_summary.json'))
        assert parsed['counts']==report['counts']
    fail=report_document([{'id':'fail','area':'x','status':'FAIL','detail':'Error'}],scope='test')
    assert fail['release_gate']=='BLOCKED'
    try: report_document([{'id':'x','area':'x','status':'UNKNOWN','detail':''}],scope='test')
    except ValueError:pass
    else: raise AssertionError('Unknown audit status accepted')
    print('PASS: Audit JSON, escaped offline HTML, ZIP contents and manual release gates')
if __name__=='__main__':main()
