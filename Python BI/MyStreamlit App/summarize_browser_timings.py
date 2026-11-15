"""Summarise optional local server-side Streamlit timings after manual browser checks."""
from __future__ import annotations
import json
from pathlib import Path
from ui_runtime_metrics import summarize

if __name__=='__main__':
    report=summarize()
    out=Path(__file__).resolve().parent/'acceptance_results'/'UI_SERVER_TIMING_SUMMARY.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Server-side render function samples:',report['samples'],' errors:',report['errors'])
    for page in report['pages']:
        print(f"{page['page']}: {page['observations']} samples; max rows {page['max_rows_observed']:,}; "
              f"median {page['median_server_seconds']:.2f}s; max {page['max_server_seconds']:.2f}s")
    print('NOTE: no browser-paint, download/network, or complete cleaning-page latency is measured.')
    print('Report:',out)
