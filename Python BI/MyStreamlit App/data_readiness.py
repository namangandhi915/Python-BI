"""Dataset scale and readiness checks with explicitly labelled sampling.

A diagnostic tool, not an assertion of 500,000-row throughput or an exhaustive
validation unless a user chooses a complete missing-value scan.
"""
from __future__ import annotations

import pandas as pd


def dataset_profile(
    data: pd.DataFrame,
    *,
    sample_limit: int = 10_000,
    exact_missing_scan: bool = False,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Return (summary, per-field profile, sampled preview), without mutation.

    Unique and duplicate values are always SAMPLE counts. Sampling is seeded.
    Full missing-value counts are calculated only when exact_missing_scan=True.
    """
    if sample_limit < 1 or sample_limit > 50_000:
        raise ValueError("Sample limit must be between 1 and 50,000 rows.")
    if not data.columns.is_unique:
        raise ValueError("The dataset contains duplicate column names; rename them before profiling.")
    total_rows, total_columns = data.shape
    count = min(sample_limit, total_rows)
    sample = data.sample(n=count, random_state=26).reset_index(drop=True) if count else data.head(0).copy()
    source_shallow_mb = float(data.memory_usage(index=True, deep=False).sum() / (1024 * 1024))
    sample_deep_mb = float(sample.memory_usage(index=True, deep=True).sum() / (1024 * 1024))
    approx_full_deep_mb = (
        float(sample_deep_mb * (total_rows / count)) if count else 0.0
    )
    sample_missing_cells = int(sample.isna().sum().sum())
    sample_duplicates = int(sample.duplicated().sum()) if total_columns else 0
    full_missing = data.isna().sum() if exact_missing_scan else None
    fields = []
    for column in data.columns:
        series = sample[column]
        fields.append({
            "Column": str(column),
            "Source dtype": str(data[column].dtype),
            "Missing in sample": int(series.isna().sum()),
            "Sample missing %": round(float(series.isna().mean() * 100), 2) if count else None,
            "Unique in sample": int(series.nunique(dropna=True)),
            **({"Exact missing in source": int(full_missing[column])} if full_missing is not None else {}),
        })
    per_column = pd.DataFrame(fields, columns=[
        "Column", "Source dtype", "Missing in sample", "Sample missing %", "Unique in sample",
        *(["Exact missing in source"] if exact_missing_scan else []),
    ])
    summary = {
        "source_rows": total_rows,
        "source_columns": total_columns,
        "sample_rows": count,
        "sample_missing_cells": sample_missing_cells,
        "sample_duplicate_rows": sample_duplicates,
        "source_shallow_memory_mb": source_shallow_mb,
        "estimated_deep_memory_mb": approx_full_deep_mb,
        "exact_missing_scan": exact_missing_scan,
        "exact_missing_cells": int(full_missing.sum()) if full_missing is not None else None,
    }
    return summary, per_column, sample
