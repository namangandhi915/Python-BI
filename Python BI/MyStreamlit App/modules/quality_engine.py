"""Python BI Studio — reusable dataset quality checks; no dataset mutation."""
from __future__ import annotations

import pandas as pd


def quality_table(data: pd.DataFrame) -> pd.DataFrame:
    """Column-by-column missing/unique/type report; safely handles empty frames."""
    rows = len(data)
    missing = data.isna().sum()
    return pd.DataFrame({
        "Column": data.columns.astype(str),
        "Data type": [str(t) for t in data.dtypes],
        "Missing values": missing.to_numpy(),
        "Missing %": (missing.to_numpy() / rows * 100 if rows else [0.0] * len(data.columns)),
        "Non-null unique": [int(data[col].nunique(dropna=True)) for col in data.columns],
    }).round({"Missing %": 2})


def missing_records(data: pd.DataFrame, column: str | None = None) -> pd.DataFrame:
    """Return actual affected records; never remove or fill missing values."""
    if column is None:
        return data.loc[data.isna().any(axis=1)].copy()
    if column not in data.columns:
        raise KeyError(f"Unknown column: {column}")
    return data.loc[data[column].isna()].copy()


def quality_overview(data: pd.DataFrame) -> dict:
    return {
        "rows": len(data),
        "columns": len(data.columns),
        "missing_cells": int(data.isna().sum().sum()),
        "rows_with_missing": int(data.isna().any(axis=1).sum()),
        "duplicate_rows": int(data.duplicated().sum()),
    }
