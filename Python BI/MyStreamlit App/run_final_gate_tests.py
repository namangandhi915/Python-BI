"""One terminal command: 5 new final-gate tests + 31 preserved prior scripts.

Superseded historical release SHA256 tests are deliberately excluded because
app.py and commerce_engine.py have changed. The new manifest verifies them.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json
import importlib.util
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
NEW=['test_final_financial.py','test_final_legacy.py','test_final_reliability.py',
     'test_final_ui_timing.py','test_final_evidence.py']

# Preserve the latest baseline's regression list, except its obsolete manifest.
from run_local_review_tests import NEW as PRIOR_NEW, OLD as PRIOR_OLD
PRIOR=[p for p in PRIOR_NEW+PRIOR_OLD if p not in ('test_local_release_manifest.py','test_design_release_manifest.py')]
TESTS=NEW+PRIOR


def run():
    results=[]
    for name in TESTS:
        target=ROOT/name
        if not target.is_file():
            results.append({'file':name,'status':'FAIL','reason':'Missing test file'})
            print('FAIL:',name,'missing')
            continue
        if importlib.util.find_spec('streamlit') is None:
            # Streamlit isn't available in the *preparation* runner. The shim
            # only lets pure calculation and existing fake-UI tests import.
            cmd=[sys.executable,'-c',
              'import sys,types;sys.modules["streamlit"]=types.SimpleNamespace();sys.argv=[sys.argv[1]];sys.modules["__main__"].__file__=sys.argv[0];exec(compile(open(sys.argv[0],encoding="utf-8").read(),sys.argv[0],"exec"),sys.modules["__main__"].__dict__)',str(target)]
        else:
            cmd=[sys.executable,str(target)]
        try:
            p=subprocess.run(cmd,cwd=ROOT,text=True,encoding='utf-8',errors='replace',
                             capture_output=True,timeout=180)
            passed=p.returncode==0
            results.append({'file':name,'status':'PASS' if passed else 'FAIL','returncode':p.returncode})
            print(('PASS' if passed else 'FAIL')+':',name)
            if not passed:
                print('    STDERR:',p.stderr[-1500:])
                print('    STDOUT:',p.stdout[-1500:])
        except subprocess.TimeoutExpired:
            results.append({'file':name,'status':'FAIL','reason':'180-second limit exceeded'})
            print('FAIL:',name,'timed out')
    summary={'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'test_results':results,'passed':sum(x['status']=='PASS' for x in results),
             'failed':sum(x['status']=='FAIL' for x in results),
             'browser_signoff':'PENDING','hosting':'NOT_AUTHORIZED'}
    output=ROOT/'acceptance_results';output.mkdir(exist_ok=True)
    (output/'FINAL_TEST_RESULTS.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('FINISHED:',summary['passed'],'passed,',summary['failed'],'failed.')
    print('Browser checks and final local academic roadmap sign-off: NOT AUTOMATED.')
    return 0 if summary['failed']==0 else 1

if __name__=='__main__':raise SystemExit(run())
