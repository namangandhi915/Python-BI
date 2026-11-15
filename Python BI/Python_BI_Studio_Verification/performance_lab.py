"""An explicitly bounded, optional local performance diagnostic.

This tool is NOT a benchmark of full-source upload, Streamlit rendering, or
500k-record readiness. Only the selected, sampled grouping operation is timed.
"""
from __future__ import annotations

from time import perf_counter

import numpy as np
import pandas as pd

MAX_BENCHMARK_ROWS = 50_000


def benchmark_grouping(
    source: pd.DataFrame, category_column: str, numeric_column: str,
    sample_limit: int = 10_000,
) -> tuple[dict, pd.DataFrame]:
    if not 1 <= int(sample_limit) <= MAX_BENCHMARK_ROWS:
        raise ValueError(f"Benchmark sample must be between 1 and {MAX_BENCHMARK_ROWS:,} rows.")
    if not source.columns.is_unique:
        raise ValueError("The dataset contains ambiguous duplicate field names.")
    if category_column not in source.columns or numeric_column not in source.columns:
        raise ValueError("Select valid category and numeric source columns.")
    if category_column == numeric_column:
        raise ValueError("Choose different category and numeric columns.")
    if not pd.api.types.is_numeric_dtype(source[numeric_column]):
        raise ValueError("The measure must be a numeric column.")

    start = perf_counter()
    # Select just two columns first. The entire source is not copied for the test.
    two_columns = source[[category_column, numeric_column]]
    sample_n = min(len(two_columns), int(sample_limit))
    if sample_n < len(two_columns):
        sample = two_columns.sample(n=sample_n, random_state=42).reset_index(drop=True)
    else:
        sample = two_columns.reset_index(drop=True).copy()
    numeric = pd.to_numeric(sample[numeric_column], errors="coerce")
    values = numeric.to_numpy(dtype=float, na_value=np.nan)
    good = np.isfinite(values)
    working = pd.DataFrame({
        "Category": sample[category_column].astype("string").fillna("(Missing)"),
        "Value": numeric,
    }).loc[good]
    grouped = working.groupby("Category", observed=True)["Value"].agg(
        Total="sum", Records="size"
    ).reset_index().sort_values("Total", ascending=False, kind="stable")
    elapsed = (perf_counter() - start) * 1_000
    return {
        "source_rows": len(source),
        "sample_rows": sample_n,
        "excluded_nonnumeric": int((~good).sum()),
        "group_count": len(grouped),
        "elapsed_ms": round(elapsed, 2),
        "sample_memory_mib": round(sample.memory_usage(index=True, deep=True).sum() / (1024 * 1024), 3),
        "full_source_benchmarked": sample_n == len(source),
    }, grouped.head(15).reset_index(drop=True)
