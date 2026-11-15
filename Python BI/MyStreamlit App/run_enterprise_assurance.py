"""Run Phase4/5 calculation acceptance, environment audit, optional module benchmark."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
from assurance_phase45 import run_phase45_checks
from assurance_project import inspect_project
from assurance_reports import report_document,bundle_audit
from assurance_performance import benchmark_workflow


def main()->int:
    parser=argparse.ArgumentParser(description='Python BI Studio offline acceptance & scale suite')
    parser.add_argument('--rows',type=int,default=10000,help='Synthetic module benchmark rows, 100 to 500000')
    parser.add_argument('--report-dir',default='assurance_results')
    parser.add_argument('--csv',default=None,help='Optional synthetic benchmark CSV, not user business data')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    dest=Path(args.report_dir)
    if not dest.is_absolute():dest=root/dest
    dest.mkdir(parents=True,exist_ok=True)
    checks=[c.as_dict() for c in run_phase45_checks()]+inspect_project(root)
    try:
        perf=benchmark_workflow(args.rows, existing_csv=args.csv)
        checks.append({'id':'PERFORMANCE-CHAIN','area':'Module integration','status':'PASS',
                       'detail':f"{args.rows:,} rows: search, quality sample, financial mapping, group and period reconciled"})
    except Exception as exc:
        perf={'error_type':type(exc).__name__,'scope':'Module integration only'}
        checks.append({'id':'PERFORMANCE-CHAIN','area':'Module integration','status':'FAIL',
                       'detail':f'{type(exc).__name__}: {exc}'})
    report=report_document(checks,scope=f'Automated acceptance + {args.rows:,}-row module test')
    (dest/'enterprise_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (dest/'performance_module_results.json').write_text(json.dumps(perf,indent=2),encoding='utf-8')
    (dest/'enterprise_acceptance_pack.zip').write_bytes(bundle_audit(report))
    for status in ('PASS','FAIL','MANUAL'):
        print(f'{status}: {report["counts"][status]}')
    print(f'RELEASE GATE: {report["release_gate"]}')
    print('Evidence: assurance_results/enterprise_acceptance.json and enterprise_acceptance_pack.zip')
    print('MANUAL items remain pending even if automated tests all pass.')
    return 1 if report['counts']['FAIL'] else 0

if __name__=='__main__':
    raise SystemExit(main())
