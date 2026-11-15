"""Data-minimised audit exports: no source row values or local file paths."""
from __future__ import annotations
from datetime import datetime, timezone
from html import escape
from io import BytesIO
import json
import zipfile

VALID = {'PASS','FAIL','MANUAL'}


def report_document(checks: list[dict], *, scope: str) -> dict:
    if not isinstance(scope, str) or len(scope)>120:
        raise ValueError('Audit scope must be a short label.')
    normalized=[]
    for item in checks:
        if item.get('status') not in VALID:
            raise ValueError('Unsupported audit status')
        normalized.append({key:str(item.get(key, '')) for key in ('id','area','status','detail')})
    stats={status:sum(c['status']==status for c in normalized) for status in ('PASS','FAIL','MANUAL')}
    return {'product':'Python BI Studio','scope':scope,
            'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'counts':stats,'release_gate':('BLOCKED' if stats['FAIL'] else 'REVIEW_REQUIRED' if stats['MANUAL'] else 'READY_FOR_REVIEW'),
            'checks':normalized,'note':'Automated PASS does not certify production security, all datasets, or visual/browser behaviour.'}


def render_html(report:dict)->str:
    rows=[]
    for check in report['checks']:
        rows.append('<tr>' + ''.join('<td>'+escape(str(check[key]), quote=True)+'</td>'
                                        for key in ('id','area','status','detail')) + '</tr>')
    header=escape(report['scope'],quote=True)
    counts=escape(str(report['counts']))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Python BI Studio — Acceptance Evidence</title>'
            '<style>body{font:16px system-ui;color:#142b4a;background:#f5f8fc;max-width:1120px;margin:40px auto;padding:18px}'
            'h1{font-size:32px}p{line-height:1.5}table{border-collapse:collapse;width:100%;background:#fff}'
            'td,th{border-bottom:1px solid #dae4ef;text-align:left;padding:12px;vertical-align:top;word-break:break-word}'
            'th{background:#e8f0fb}@media print{body{background:white}}</style></head><body>'
            '<h1>Python BI Studio — Acceptance Evidence</h1><p><strong>Scope:</strong> '+header+'</p>'
            '<p><strong>Result:</strong> '+escape(report['release_gate'])+' · '+counts+'</p>'
            '<p>Automated tests are not a substitute for production acceptance or security review.</p>'
            '<table><thead><tr><th>Check ID</th><th>Area</th><th>Status</th><th>Evidence</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></body></html>')


def bundle_audit(report:dict)->bytes:
    target=BytesIO()
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('acceptance_summary.json', json.dumps(report,indent=2,ensure_ascii=False))
        zf.writestr('acceptance_summary.html', render_html(report))
        zf.writestr('README.txt','Contains automated and pending/manual acceptance evidence only; no raw source transactions.\n')
    return target.getvalue()
