"""One combined terminal run: new local-only checks and preserved regressions."""
from __future__ import annotations
import argparse, importlib.util, json, subprocess, sys
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent
NEW=[
    'test_local_file_guard.py','test_local_recovery.py','test_sector_acceptance.py',
    'test_professor_review.py','test_local_launcher.py','test_local_app_wiring.py',
    'test_local_workload.py','test_synthetic_sector_data.py','test_no_review_panel.py',
    'test_local_release_manifest.py',
]
OLD=[
    'test_design_system.py','test_deployment_audit.py','test_release_evidence.py',
    'test_operations_ui_mock.py','test_design_integration.py',
    # Old design-release manifest validates the PREVIOUS app.py intentionally;
    # it is superseded by the new local release manifest.
    'test_assurance_contracts.py','test_phase45_acceptance.py',
    'test_assurance_reports.py','test_assurance_performance.py','test_assurance_ui_mock.py',
    'test_scale_batch12.py','test_explorer_ui_mock.py',
    'test_investment_foundation.py','test_investment_forecasting.py',
    'test_ui_integration_local.py',
    'test_phase3_batch2.py','test_phase3_batch34.py','test_phase3_batch56.py',
    'test_phase3_batch78.py','test_phase3_batch910.py',
    'test_phase3_batch1112.py','test_phase3_batch1314.py',
]

def run(fast=False):
    results=[]
    for file in (NEW if fast else NEW+OLD):
        path=ROOT/file
        if not path.is_file():
            results.append({'test':file,'status':'FAIL','reason':'Missing file'})
            print('FAIL:',file,'not found')
            continue
        try:
            # The preparation environment may not include Streamlit. In that
            # case pure calculations/UI mocks use a stub in the CHILD process
            # only. A real installed Streamlit is always used on the user's PC.
            if importlib.util.find_spec('streamlit') is None:
                cmd=[sys.executable,'-c',
                     'import sys,types;sys.modules["streamlit"]=types.SimpleNamespace();sys.argv=[sys.argv[1]];sys.modules["__main__"].__file__=sys.argv[0];exec(compile(open(sys.argv[0],encoding="utf-8").read(),sys.argv[0],"exec"),sys.modules["__main__"].__dict__)',
                     str(path)]
            else:
                cmd=[sys.executable,str(path)]
            proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,
                text=True,encoding='utf-8',errors='replace',timeout=180)
            ok=proc.returncode==0
            results.append({'test':file,'status':'PASS' if ok else 'FAIL',
                            'exit_code':proc.returncode})
            print(('PASS' if ok else 'FAIL')+':',file)
            if not ok:
                print('   Failed test; run this file directly to see the details.')
        except subprocess.TimeoutExpired:
            results.append({'test':file,'status':'FAIL','reason':'Timeout 180 seconds'})
            print('FAIL:',file,'timed out')
    report={'date_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'scope':'Local-only automated checks; browser and academic review still manual',
            'results':results,'passed':sum(x['status']=='PASS' for x in results),
            'failed':sum(x['status']=='FAIL' for x in results)}
    folder=ROOT/'professor_results';folder.mkdir(exist_ok=True)
    (folder/'LOCAL_TEST_RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('FINISHED:',report['passed'],'passed,',report['failed'],'failed.')
    print('Browser review, external approval and public hosting are NOT included.')
    return 0 if report['failed']==0 else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fast',action='store_true')
    raise SystemExit(run(parser.parse_args().fast))
