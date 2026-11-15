"""Run the new release tests plus all verified financial/investment regressions.

Outputs only test file names, results and summary. Actual browser testing remains manual.
"""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
import argparse
import json
import subprocess
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = PROJECT_ROOT
NEW = [
    'test_design_system.py', 'test_deployment_audit.py', 'test_release_evidence.py',
    'test_operations_ui_mock.py', 'test_design_integration.py', 'test_design_release_manifest.py',
]
REGRESSION = [
    'test_assurance_contracts.py','test_phase45_acceptance.py',
    'test_assurance_reports.py','test_assurance_performance.py','test_assurance_ui_mock.py',
    'test_scale_batch12.py','test_explorer_ui_mock.py',
    'test_investment_foundation.py','test_investment_forecasting.py',
    'test_ui_integration_local.py',
    'test_phase3_batch2.py','test_phase3_batch34.py','test_phase3_batch56.py',
    'test_phase3_batch78.py','test_phase3_batch910.py',
    'test_phase3_batch1112.py','test_phase3_batch1314.py',
]

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Python BI Studio local release tests')
    parser.add_argument('--fast',action='store_true',help='Run new tests only; skip earlier regression suite')
    args=parser.parse_args(argv)
    suite = NEW if args.fast else NEW + REGRESSION
    results=[]
    for test in suite:
        if not (BASE / 'tests' / test).is_file():
            results.append({'name': test,'status':'FAIL','reason':'Test file absent'})
            print(f'FAIL | {test} | File absent')
            continue
        try:
            process=subprocess.run(
                [sys.executable, str(BASE/'tests'/test)],cwd=BASE,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONPATH": os.pathsep.join([str(BASE), str(BASE/"modules"), str(BASE/"scripts"), os.environ.get("PYTHONPATH", "")])},
                text=True,timeout=180, encoding='utf-8',errors='replace',
            )
            ok=process.returncode==0
            results.append({'name':test,'status':'PASS' if ok else 'FAIL','exit_code':process.returncode})
            print(f'{"PASS" if ok else "FAIL"} | {test}')
            if not ok:
                print('   Review this script directly for details:',test)
        except subprocess.TimeoutExpired:
            results.append({'name':test,'status':'FAIL','reason':'Timeout after 180 seconds'})
            print('FAIL |',test,'| Timeout')
    dest=BASE/'outputs'/'release_results'
    dest.mkdir(parents=True,exist_ok=True)
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'scope':'Local automated syntax/calculation/integration checks; browser and security gates remain manual',
            'mode':'fast' if args.fast else 'full',
            'results':results,'passed':sum(x['status']=='PASS' for x in results),
            'failed':sum(x['status']=='FAIL' for x in results)}
    (dest/'regression_tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'FINISHED: {report["passed"]} passed, {report["failed"]} failed. Browser/manual gates remain.')
    return 1 if report['failed'] else 0

if __name__=='__main__':raise SystemExit(main())
