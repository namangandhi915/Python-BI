"""Opt-in, local-only Streamlit server-side render timing. No dataset values/names.

Set PYTHON_BI_UI_METRICS=1 *before* starting Streamlit; generated JSONL is
local, outside the website. Does not measure browser painting or network time.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import json
import os
from collections import defaultdict
from functools import wraps

ROOT = Path(__file__).resolve().parents[1]
TIMINGS = ROOT / 'outputs' / 'acceptance_results' / 'ui_server_timings.jsonl'
VALID_PAGES = {'Home','Home assurance','Home readiness','Explorer','Commercial Intelligence',
               'Business Planning','Investment Intelligence','Executive Dashboard','Legacy compatible view'}


def enabled() -> bool:
    return os.environ.get('PYTHON_BI_UI_METRICS', '').strip() == '1'


def _rss_mib():
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / (1024*1024), 2)
    except (ImportError, OSError):
        return None


def tracked_render(page: str, fn, *args, **kwargs):
    if not enabled():
        return fn(*args, **kwargs)
    if page not in VALID_PAGES:
        raise ValueError('Unknown predefined page timing label.')
    rows = cols = None
    for arg in args:
        if hasattr(arg, 'shape') and len(getattr(arg, 'shape', ())) == 2:
            rows, cols = int(arg.shape[0]), int(arg.shape[1])
            break
    start_mem = _rss_mib()
    start = perf_counter()
    status = 'PASS'
    error_kind = None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        status = 'ERROR'
        error_kind = type(exc).__name__  # Never store exception messages or user data
        raise
    finally:
        info = {
            'timestamp_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'page':page,'records':rows,'columns':cols,
            'seconds':round(perf_counter()-start,4), 'rss_before_mib':start_mem,
            'rss_after_mib':_rss_mib(), 'status':status,'error_class':error_kind,
            'scope':'server-side selected render function; excludes browser/network'
        }
        try:
            TIMINGS.parent.mkdir(parents=True,exist_ok=True)
            if TIMINGS.exists() and TIMINGS.stat().st_size > 2_000_000:
                # Keep logging bounded, not an unbounded growing run history.
                TIMINGS.rename(TIMINGS.with_suffix('.previous.jsonl'))
            with TIMINGS.open('a', encoding='utf-8') as out:
                out.write(json.dumps(info, separators=(',', ':'))+'\n')
        except (OSError, TypeError):
            pass  # Never fail the actual Streamlit page because telemetry failed.


def summarize(path: Path | None = None) -> dict:
    location = Path(path) if path else TIMINGS
    groups = defaultdict(list)
    errors = 0
    if location.exists():
        for line in location.read_text(encoding='utf-8').splitlines():
            try:
                record = json.loads(line)
                if record.get('page') not in VALID_PAGES:
                    continue
                groups[record['page']].append(record)
                errors += record.get('status') != 'PASS'
            except (json.JSONDecodeError, KeyError):
                continue
    summary = []
    for page, records in sorted(groups.items()):
        elapsed = sorted(float(r['seconds']) for r in records)
        summary.append({'page':page,'observations':len(records),
                        'max_rows_observed':max((r.get('records') or 0) for r in records),
                        'median_server_seconds':elapsed[(len(elapsed)-1)//2],
                        'max_server_seconds':max(elapsed),
                        'last_rss_mib':records[-1].get('rss_after_mib'),
                        'errors':sum(r['status']!='PASS' for r in records)})
    return {'measurement':'Server-side selected render functions only, not complete browser latency',
            'samples':sum(len(s) for s in groups.values()),'errors':int(errors), 'pages':summary,
            'browser_acceptance':'MANUAL'}


def instrument(page: str, fn):
    """Wrap an existing view without changing its original UI call site."""
    @wraps(fn)
    def measured(*args, **kwargs):
        return tracked_render(page, fn, *args, **kwargs)
    return measured
