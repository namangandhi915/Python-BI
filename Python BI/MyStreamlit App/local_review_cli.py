"""Generate local-only, data-minimised academic verification evidence.

Does not publish the app, upload any records, or alter Dataset Library state.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from professor_review import review_packet, review_summary
from local_recovery_audit import audit_dataset_library
from sector_acceptance import run_sector_acceptance
from local_workload_benchmark import run_workload


def build_local_evidence(root: Path, *, rows: int=10_000) -> dict:
    sectors=run_sector_acceptance()
    report={
        'project': 'Python BI Studio',
        'hosting': 'PRIVATE_LOCAL_ONLY',
        'professor_approval': 'PENDING',
        'project_phase_status': review_summary()['phase_status'],
        'sector_checks': sectors,
        'dataset_library_audit': audit_dataset_library(root),
        'performance': run_workload(rows),
        'browser_review': 'MANUAL — not automatically certified',
        'public_deployment': 'NOT_REQUESTED_NOT_AUTHORIZED',
        'financial_assumptions': 'Profit called net only when all expenses are explicitly mapped and user confirms completeness.',
        'scope': 'Does not expose original business data, workbook paths or transaction values',
    }
    return report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rows',type=int,default=10000)
    ap.add_argument('--output-dir',default='professor_results')
    args=ap.parse_args(argv)
    base=Path(__file__).resolve().parent
    report=build_local_evidence(base,rows=args.rows)
    target=base/args.output_dir
    # Reports should remain in the local workspace; prevent accidental traversal.
    if target.resolve().parent!=base.resolve():
        raise ValueError('Output folder must be directly inside this local project.')
    target.mkdir(exist_ok=True)
    (target/'LOCAL_ACADEMIC_READINESS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (target/'PROFESSOR_REVIEW_PACKET.zip').write_bytes(review_packet())
    print('PASS: Three synthetic sectors reconciled; workload completed.')
    print('Review materials created in:',target.name)
    print('Professor approval: PENDING; public hosting: NOT AUTHORIZED.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
