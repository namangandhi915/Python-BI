"""Generate local, record-free final roadmap acceptance evidence (no hosting).

Automated module/fixture tests run immediately. Browser, real accounting data,
professional evaluation and public hosting are NOT auto-approved.
"""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
import argparse
from datetime import datetime,timezone
from html import escape
import json
from pathlib import Path
import zipfile
from final_financial_checks import financial_edge_suite
from final_reliability_checks import run_recovery_checks
from local_workload_benchmark import run_workload
from ui_runtime_metrics import summarize

ROOT=PROJECT_ROOT
OUT=ROOT/'outputs'/'acceptance_results'
GATES=[
 ('G1','Multi-schema Dashboard compatibility','Different valid schemas, legacy safety, null/empty filters','Compare classic practice workbook against 3 alternate-sector CSVs in Streamlit.'),
 ('G2','Independent accounting and financial reconciliation','Revenue, costs, discounts, returns, taxes, ROI and report consistency','Check mapping semantics against representative actual source/accounting definitions.'),
 ('G3','Full-application performance','Synthetic search/quality/finance/chart/report module workload','Perform timed Streamlit interactions at 10k, 100k, and 500k where feasible.'),
 ('G4','Edge reliability, safe exports and recovery','Temporary-only library integrity, invalid uploads, CSV/HTML exports','Verify actual restart, saved-dataset restoration, empty results and browser exports.'),
 ('G5','Technical roadmap sign-off evidence','Generates tested release evidence and manual acceptance matrix','Complete manual gates, record limitations, obtain your own final confirmation.')
]


def html_table(rows, columns):
    heading=''.join('<th>'+escape(str(col))+'</th>' for col in columns)
    body=''.join('<tr>'+''.join('<td>'+escape(str(row.get(col,'')))+'</td>' for col in columns)+'</tr>' for row in rows)
    return '<table><thead><tr>'+heading+'</tr></thead><tbody>'+body+'</tbody></table>'


def make_html(report):
    gates=report['gates']
    rows=[{'Gate':g['id'],'Area':g['name'],'Automated':'PASS' if g['automated']=='PASS' else 'FAIL',
           'Browser / sign-off':'PENDING'} for g in gates]
    failed=[r for r in report['automated_checks'] if r['status']=='FAIL']
    fails=''.join('<li>'+escape(x['id']+': '+x['detail'])+'</li>' for x in failed)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Python BI Studio / Final Acceptance Evidence</title><style>
body{{font:16px/1.5 Segoe UI,Arial,sans-serif;color:#26364a;background:#f5f8fc;margin:0}}main{{max-width:1080px;margin:28px auto;background:white;padding:34px;border-radius:12px}}
h1{{color:#142b4a;font-size:30px}}h2{{color:#142b4a;margin-top:30px}}.eyebrow{{color:#2878e5;text-transform:uppercase;font-size:12px;letter-spacing:.12em;font-weight:bold}}
.note{{background:#f2f6fc;padding:15px;border-left:4px solid #2878e5}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:10px;border-bottom:1px solid #dce5f0;text-align:left}}th{{background:#edf3fb}}@media print{{body{{background:white}}main{{margin:0;padding:0}}}}
</style></head><body><main><div class="eyebrow">Private local application / Quality assurance</div>
<h1>Final Roadmap Acceptance Evidence</h1><p><b>Generated:</b> {escape(report['utc_generated'])} UTC</p>
<div class="note"><b>Current gate:</b> {escape(report['release_status'])}<p>Automated fixture/module checks are distinct from actual Windows Streamlit browser checks. No public hosting, raw business records, usernames, saved paths or real accounting records are included.</p></div>
<h2>Five acceptance gates</h2>{html_table(rows,['Gate','Area','Automated','Browser / sign-off'])}
<h2>Automated checks</h2><p>{report['pass_count']} passed / {report['fail_count']} failed. Synthetic workload: {report['workload']['rows']:,} rows.</p>
{html_table(report['automated_checks'],['id','title','status'])}
<h2>Issues</h2>{'<ul>'+fails+'</ul>' if fails else '<p>None in automated checks.</p>'}
<h2>Full application performance</h2><p>{escape(report['ui_metrics']['measurement'])}. Samples collected: {report['ui_metrics']['samples']}.</p>
<h2>Required follow-up</h2><p>Complete manual browser checks in docs/05_GATE_BROWSER_CHECKLIST.md and assess financial column meaning in a real business dataset. Keep local-only mode. Original roadmap Phase 6 calibrated AI predictions and live-market feeds are not implemented; do not describe them as completed.</p>
<footer>Python BI Studio — offline evidence, not academic sign-off or production security certification.</footer></main></body></html>'''


def run(rows=10_000):
    if rows not in (10_000,100_000,500_000):
        raise ValueError('Rows must be exactly 10000, 100000 or 500000.')
    OUT.mkdir(parents=True,exist_ok=True)
    finance=financial_edge_suite()
    recovery=run_recovery_checks()
    all_checks=finance+recovery
    benchmark=None
    try:
        benchmark=run_workload(rows)
        all_checks.append({'id':'G3-MODULE','title':f'{rows:,}-row synthetic module-chain benchmark','status':'PASS',
                           'detail':'Search, quality, filters, mapped financials, chart prep, report and CSV checks'})
    except Exception as exc:
        all_checks.append({'id':'G3-MODULE','title':'Synthetic module-chain benchmark','status':'FAIL',
                           'detail':type(exc).__name__+': '+str(exc)})
        benchmark={'rows':rows,'status':'FAIL','streamlit_full_ui_certified':False,'steps_sec':{}}
    checks_by_gate={
        'G1':[x for x in all_checks if x['id'].startswith('F4-') or x['id'].startswith('F45-SECTOR')],
        'G2':[x for x in all_checks if x['id'].startswith('F5-') or x['id']=='F7-01'],
        'G3':[x for x in all_checks if x['id']=='G3-MODULE'],
        'G4':[x for x in all_checks if x['id'].startswith('G4-') or x['id'].startswith('F7-')],
        'G5':all_checks,
    }
    gates=[]
    for gate,name,automated,manual in GATES:
        subset=checks_by_gate[gate]
        gates.append({'id':gate,'name':name,'automated':'PASS' if all(x['status']=='PASS' for x in subset) else 'FAIL',
                      'automated_scope':automated,'browser_or_real_data':'PENDING',
                      'pending_requirement':manual})
    status='AUTOMATED_PASS__MANUAL_ACCEPTANCE_PENDING' if all(x['status']=='PASS' for x in all_checks) else 'AUTOMATED_FAILURES_TO_CORRECT'
    report={'application':'Python BI Studio','scope':'Local-only final original roadmap QA',
            'utc_generated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'release_status':status,'gates':gates,'automated_checks':all_checks,
            'pass_count':sum(x['status']=='PASS' for x in all_checks),
            'fail_count':sum(x['status']=='FAIL' for x in all_checks),
            'workload':benchmark,'ui_metrics':summarize(),
            'actual_browser_passed':False,'external_approval':'NOT_REQUESTED',
            'public_hosting':'NOT_AUTHORIZED',
            'known_limitations':['No trained/calibrated AI forecasting model or live market provider integration.',
                                 'Server-side render timings are not browser-load certification.',
                                 'Mapped financial results require correct accounting assumptions and consistent currency.',
                                 'Legacy tutorial view retains practice-workbook assumptions when schema accepted.']}
    json_file=OUT/'FINAL_ACCEPTANCE_REPORT.json'
    html_file=OUT/'FINAL_ACCEPTANCE_REPORT.html'
    json_file.write_text(json.dumps(report,indent=2),encoding='utf-8')
    html_file.write_text(make_html(report),encoding='utf-8')
    evidence=OUT/'FINAL_ACCEPTANCE_EVIDENCE.zip'
    with zipfile.ZipFile(evidence,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(json_file,json_file.name);bundle.write(html_file,html_file.name)
        for name in ('05_GATE_BROWSER_CHECKLIST.md','ACCOUNTING_ASSUMPTIONS.md',
                     'ROADMAP_FINAL_STATUS.md','LOCAL_RESTART_AND_BACKUP.md'):
            file=ROOT/'docs'/name
            if file.exists():bundle.write(file,'docs/'+name)
        test_result=OUT/'FINAL_TEST_RESULTS.json'
        if test_result.exists():bundle.write(test_result,test_result.name)
        ui=OUT/'UI_SERVER_TIMING_SUMMARY.json'
        if ui.exists():bundle.write(ui,ui.name)
    print('Acceptance:',status)
    print('Automated:',report['pass_count'],'PASS,',report['fail_count'],'FAIL')
    print('Module-chain synthetic row count:',rows)
    print('Real Streamlit browser and final approval: PENDING')
    print('Output:',evidence)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows',type=int,choices=[10000,100000,500000],default=10000)
    args=parser.parse_args()
    result=run(args.rows)
    raise SystemExit(0 if result['fail_count']==0 else 1)
