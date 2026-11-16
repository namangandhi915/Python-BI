"""Pure full-dataset Explorer operations for Python BI Studio.

Select minimal columns, search in fixed-size chunks and count *all* matching
records before applying a display limit. No changes are made to source data.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Sequence

import numpy as np
import pandas as pd

DEFAULT_CHUNK_SIZE = 20_000
MAX_PREVIEW_ROWS = 1_000_000
MAX_EXPORT_ROWS = 1_000_000


@dataclass(frozen=True)
class ExplorerMeta:
    source_rows: int
    matched_rows: int
    shown_rows: int
    exported_rows: int
    export_truncated: bool
    scan_seconds: float
    preview_seconds: float
    total_seconds: float
    search_scope: str = "Entire active dataset"


def _valid_columns(source: pd.DataFrame, selected: Sequence[str]) -> list[str]:
    if not source.columns.is_unique:
        raise ValueError("Duplicate source column names must be resolved before exploration.")
    if not source.columns.map(lambda x: isinstance(x, str)).all():
        raise ValueError("Source column names must be text.")
    if not selected:
        raise ValueError("Select at least one column.")
    if len(set(selected)) != len(selected):
        raise ValueError("Selected columns must be unique.")
    if any(column not in source.columns for column in selected):
        raise ValueError("An unknown column was selected.")
    return list(selected)


def literal_search_mask(
    source: pd.DataFrame,
    columns: Sequence[str],
    term: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> np.ndarray:
    """Case-insensitive literal OR search across *all rows*, with bounded chunks."""
    checked = _valid_columns(source, columns)
    if not isinstance(term, str):
        raise ValueError("Search text must be a string.")
    if not 1 <= int(chunk_size) <= 100_000:
        raise ValueError("Chunk size must be between 1 and 100,000.")
    phrase = term.strip()
    count = len(source)
    if not phrase:
        return np.ones(count, dtype=bool)
    result = np.zeros(count, dtype=bool)
    for start in range(0, count, int(chunk_size)):
        end = min(start + int(chunk_size), count)
        chunk_match = np.zeros(end - start, dtype=bool)
        for column in checked:
            if chunk_match.all():
                break
            column_text = source[column].iloc[start:end].astype("string")
            found = column_text.str.contains(phrase, case=False, regex=False, na=False)
            chunk_match |= found.to_numpy(dtype=bool, na_value=False)
        result[start:end] = chunk_match
    return result


def build_filter_mask(
    source: pd.DataFrame,
    selected: Sequence[str],
    search_text: str = "",
    *,
    category_column: str | None = None,
    category_values: Sequence[str] | None = None,
    numeric_column: str | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> np.ndarray:
    """Apply filters to *all records*, preserving duplicate row indices."""
    checked = _valid_columns(source, selected)
    mask = literal_search_mask(source, checked, search_text, chunk_size=chunk_size)
    if category_column is not None:
        if category_column not in checked:
            raise ValueError("Category field must be a selected column.")
        if category_values is None:
            raise ValueError("Category values must be provided.")
        if len(category_values) == 0:
            return np.zeros(len(source), dtype=bool)
        options = list(category_values)
        mask &= source[category_column].astype("string").isin(options).to_numpy(dtype=bool)
    if numeric_column is not None:
        if numeric_column not in checked:
            raise ValueError("Numeric field must be a selected column.")
        if minimum is None or maximum is None:
            raise ValueError("Both numeric range limits are required.")
        lower, upper = float(minimum), float(maximum)
        if not (np.isfinite(lower) and np.isfinite(upper) and lower <= upper):
            raise ValueError("Numeric bounds must be finite and ascending.")
        values = pd.to_numeric(source[numeric_column], errors="coerce")
        mask &= values.between(lower, upper).fillna(False).to_numpy(dtype=bool)
    return mask


def explore_dataset(
    source: pd.DataFrame,
    selected: Sequence[str],
    *,
    search_text: str = "",
    category_column: str | None = None,
    category_values: Sequence[str] | None = None,
    numeric_column: str | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    sort_column: str | None = None,
    ascending: bool = True,
    preview_limit: int = 100,
    export_limit: int = MAX_EXPORT_ROWS,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[pd.DataFrame, pd.DataFrame, ExplorerMeta]:
    """Return small preview and capped export, with accurate full-data match count.

    Sorting uses a stable full-result order but only selected columns are copied.
    The export is unambiguously capped, never presented as full when truncated.
    """
    checked = _valid_columns(source, selected)
    if not 1 <= int(preview_limit) <= MAX_PREVIEW_ROWS:
        raise ValueError(f"Preview must contain 1–{MAX_PREVIEW_ROWS:,} records.")
    if not 1 <= int(export_limit) <= MAX_EXPORT_ROWS:
        raise ValueError(f"Export must contain 1–{MAX_EXPORT_ROWS:,} records.")
    if sort_column is not None and sort_column not in checked:
        raise ValueError("Sort field must be a selected column.")
    start = perf_counter()
    mask = build_filter_mask(
        source, checked, search_text,
        category_column=category_column, category_values=category_values,
        numeric_column=numeric_column, minimum=minimum, maximum=maximum,
        chunk_size=chunk_size,
    )
    scan_seconds = perf_counter() - start
    positions = np.flatnonzero(mask)
    matched = len(positions)
    if sort_column is not None and matched:
        # Sorting the whole selected result is deliberate and may cost memory.
        selected_sort = source[sort_column].iloc[positions].reset_index(drop=True)
        order = selected_sort.sort_values(ascending=bool(ascending), kind="stable", na_position="last").index.to_numpy()
        positions = positions[order]
    preview_positions = positions[:int(preview_limit)]
    export_positions = positions[:int(export_limit)]
    preview = source.iloc[preview_positions][checked].reset_index(drop=True).copy()
    export = source.iloc[export_positions][checked].reset_index(drop=True).copy()
    elapsed = perf_counter() - start
    meta = ExplorerMeta(
        source_rows=len(source), matched_rows=matched, shown_rows=len(preview),
        exported_rows=len(export), export_truncated=matched > len(export),
        scan_seconds=round(scan_seconds, 4),
        preview_seconds=round(elapsed - scan_seconds, 4),
        total_seconds=round(elapsed, 4),
    )
    return preview, export, meta


def safe_preview(frame: pd.DataFrame) -> pd.DataFrame:
    """Display-safe conversion applies to bounded preview ONLY."""
    preview = frame.copy()
    for column in preview.select_dtypes(include=["object"]).columns:
        preview[column] = preview[column].astype("string").fillna("")
    return preview
