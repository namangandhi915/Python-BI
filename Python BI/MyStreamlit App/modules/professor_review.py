"""Data-minimised academic review packet and honest eight-phase status."""
from __future__ import annotations
from html import escape
from io import BytesIO, StringIO
from datetime import datetime, timezone
import csv
import json
import zipfile

PHASES = (
    ('1', 'Corporate website foundation', 'CORE_VERIFIED', 'Final professor presentation review pending'),
    ('2', 'Dataset Library and persistence', 'LOCALLY_VERIFIED', 'Local single-user workflow'),
    ('3', 'Advanced Data Workspace', 'VERIFIED', '14 development batches confirmed'),
    ('4', 'Executive dashboards and charts', 'CORE_VERIFIED', 'Additional multi-schema UI acceptance pending'),
    ('5', 'Business and commerce intelligence', 'CORE_VERIFIED', 'Accounting assumptions and real-sector validation pending'),
    ('6', 'Investment Intelligence', 'RESEARCH_VERIFIED', 'Scenarios and historical bootstrap; no guaranteed forecasts'),
    ('7', 'Reports and exports', 'CORE_VERIFIED', 'HTML, CSV, ZIP; final professor demo review pending'),
    ('8', 'Performance and final release', 'LOCAL_TESTING', '500k upload/search confirmed; broader workloads & professor approval pending'),
)

CHECKS = (
    ('Home page and corporate light design', 'MANUAL'),
    ('Original Dataset Library restore / switching', 'MANUAL'),
    ('Full-dataset search with original/synthetic files', 'MANUAL'),
    ('Prepare & Validate, missing-value finder', 'MANUAL'),
    ('Commercial financial mapping and accounting assumptions', 'MANUAL'),
    ('Executive Dashboard, filters, Chart Studio', 'MANUAL'),
    ('Professional report HTML/CSV/ZIP and reconciliations', 'MANUAL'),
    ('Business investment NPV/IRR/scenarios', 'MANUAL'),
    ('Market historical research, simulation/backtest limitations', 'MANUAL'),
    ('Large-row workload and memory responsiveness', 'MANUAL'),
    ('Local-only access; no public URL', 'MANUAL'),
    ('Professor assessment, comments and approval', 'AWAITING_PROFESSOR'),
)


def review_summary() -> dict:
    return {"product": "Python BI Studio", "operating_mode": "PRIVATE_LOCAL_ONLY",
            "academic_approval": "NOT_YET_REQUESTED", "public_hosting": "NOT_AUTHORIZED",
            "phase_status": [dict(zip(('phase','area','status','note'), row)) for row in PHASES],
            "disclaimer": "These are project history milestones, not a certificate of full accounting or production readiness."}


def checklist_csv() -> str:
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['Review item', 'Initial status', 'Observed result', 'Professor comments'])
    writer.writerows((name, status, '', '') for name, status in CHECKS)
    return out.getvalue()


def review_html() -> str:
    rows = ''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in r)+'</tr>' for r in PHASES)
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<title>Python BI Studio — Professor Review</title>'
            '<style>body{font:16px system-ui;color:#142B4A;background:#f5f8fc;max-width:1050px;margin:40px auto;padding:24px}'
            'h1{font-size:32px}table{border-collapse:collapse;width:100%;background:#fff}'
            'td,th{border-bottom:1px solid #ddd;padding:12px;text-align:left;vertical-align:top}'
            '@media print{body{background:#fff}}</style>'
            '<h1>Python BI Studio</h1><p>Academic demonstration — private local application; not publicly hosted.</p>'
            '<p>The professor has not yet reviewed or approved this project.</p>'
            '<table><thead><tr><th>Phase</th><th>Area</th><th>Current status</th><th>Outstanding</th></tr></thead><tbody>'
            +rows+'</tbody></table></html>')


def review_packet() -> bytes:
    """No business data, names, machine paths or screenshots are included."""
    target=BytesIO()
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('PROJECT_STATUS.json',json.dumps(review_summary(),indent=2))
        archive.writestr('PROFESSOR_REVIEW.html',review_html())
        archive.writestr('VERIFICATION_CHECKLIST.csv',checklist_csv())
        archive.writestr('README.txt','Private local academic review packet. No raw transactions included.\n'
                         'The professor must independently assess the final application.\n')
    return target.getvalue()
