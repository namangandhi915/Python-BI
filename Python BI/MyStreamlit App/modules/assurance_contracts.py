"""Read-only, sampled dataset contracts for the Python BI Studio Home assurance view.

No raw observations are returned in the standard summary. Full-source scans are
opt-in; every sampled metric is explicitly labelled. No network/filesystem I/O.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any
import pandas as pd

DEFAULT_SAMPLE = 2000
MAX_SAMPLE = 1_000_000


def schema_fingerprint(frame: pd.DataFrame) -> str:
    spec = tuple((str(name), str(dtype)) for name, dtype in frame.dtypes.items())
    return sha256(repr(spec).encode('utf-8')).hexdigest()[:16]


def inspect_dataset(frame: pd.DataFrame | None, *, sample_size: int = DEFAULT_SAMPLE,
                    exact: bool = False) -> tuple[dict[str, Any], pd.DataFrame]:
    """Schema/quality summary and column diagnostics; sample deterministic.

    A row-count/column-count result is always source-wide. Missing/duplicates are
    sample-only except when `exact=True`. No raw business values are exported.
    """
    if frame is None:
        return {'status': 'no_active_dataset', 'rows': 0, 'columns': 0,
                'scope': 'none', 'sample_rows': 0}, pd.DataFrame()
    if not isinstance(frame, pd.DataFrame):
        raise TypeError('Active dataset must be a Pandas DataFrame.')
    if not isinstance(sample_size, int) or not 1 <= sample_size <= MAX_SAMPLE:
        raise ValueError(f'Sample size must be between 1 and {MAX_SAMPLE:,}.')
    if not frame.columns.is_unique:
        raise ValueError('Duplicate column names make dataset checks ambiguous.')
    if not all(isinstance(v, str) for v in frame.columns):
        raise ValueError('All column names must be text.')
    rows, cols = frame.shape
    count = min(rows, sample_size)
    sampled = (frame if count == rows else
               frame.sample(n=count, random_state=61).reset_index(drop=True)
               if count else frame.iloc[:0])
    missing = frame.isna().sum() if exact else sampled.isna().sum()
    duplicates = (int(frame.duplicated().sum()) if exact and cols else
                  int(sampled.duplicated().sum()) if cols else 0)
    profiles = pd.DataFrame({
        'Column': list(frame.columns),
        'Source dtype': [str(value) for value in frame.dtypes],
        'Missing values': [int(missing[column]) for column in frame.columns],
        'Missing % of checked rows': [round(float(missing[column]) / (rows if exact else count) * 100, 3)
                                      if (rows if exact else count) else 0.0 for column in frame.columns],
        'Checked scope': ['All source rows' if exact else 'Deterministic sample'] * cols,
    })
    result = {
        'status': 'ready' if rows and cols else 'empty_dataset',
        'rows': rows,
        'columns': cols,
        'sample_rows': count,
        'scope': 'entire_source' if exact else 'sample_only',
        'checked_missing_cells': int(missing.sum()),
        'checked_duplicate_rows': duplicates,
        'schema_fingerprint': schema_fingerprint(frame),
        'numeric_column_count': len(frame.select_dtypes(include='number').columns),
        'text_column_count': len(frame.select_dtypes(include=['object','string','category']).columns),
        'has_revenue_candidate': any(str(c).lower() in {'sales','revenue','gross revenue','net revenue'} for c in frame.columns),
        'has_cost_candidate': any(str(c).lower() in {'total cost','cost','cogs','cost of sales'} for c in frame.columns),
    }
    return result, profiles


def readiness_notes(summary: dict[str, Any]) -> list[str]:
    if summary.get('status') == 'no_active_dataset':
        return ['Activate a dataset from Dataset Library to inspect its schema.']
    notes = []
    if not summary.get('rows'):
        notes.append('Source contains no records; analytical checks cannot be completed.')
    if not summary.get('has_revenue_candidate'):
        notes.append('A revenue mapping must be chosen manually; no standard revenue column name detected.')
    if not summary.get('has_cost_candidate'):
        notes.append('No standard cost column name detected; profit calculations require an explicit cost mapping.')
    if summary.get('scope') == 'sample_only':
        notes.append('Missing-value and duplicate counts are from a sample, not exact source-wide counts.')
    return notes
