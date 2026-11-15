from tempfile import TemporaryDirectory
from pathlib import Path
import os
import json
import ui_runtime_metrics as m
from ui_runtime_metrics import tracked_render
with TemporaryDirectory() as folder:
    prev=m.TIMINGS; original=os.environ.get('PYTHON_BI_UI_METRICS')
    try:
        m.TIMINGS=Path(folder)/'timings.jsonl'
        os.environ['PYTHON_BI_UI_METRICS']='1'
        assert tracked_render('Explorer',lambda x:x+1,41)==42
        try:tracked_render('Home',lambda:1/0)
        except ZeroDivisionError:pass
        else:raise AssertionError('Exception swallowed')
        report=m.summarize()
        assert report['samples']==2 and report['errors']==1
        saved=m.TIMINGS.read_text()
        assert 'Explorer' in saved and 'Home' in saved
        assert 'sensitive_business_name' not in saved
        os.environ['PYTHON_BI_UI_METRICS']='0'
        assert tracked_render('Explorer',lambda:'working')=='working'
        assert m.summarize()['samples']==2
    finally:
        m.TIMINGS=prev
        if original is None:os.environ.pop('PYTHON_BI_UI_METRICS',None)
        else:os.environ['PYTHON_BI_UI_METRICS']=original
print('PASS: Explicit opt-in local server render timing, error preservation, bounded record-free log')
