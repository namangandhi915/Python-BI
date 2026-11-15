"""Stable financial export names and guarded CSV for spreadsheet applications.

Pure Python/Pandas; does not change the user's original dataset. All prefixes
are BI_... for easy filtering in Excel, Power BI and Pandas.
"""
from __future__ import annotations

import re
import pandas as pd


def _safe_header(name: object) -> str:
    name = re.sub(r"[^0-9A-Za-z]+", "_", str(name)).strip("_")
    return name or "Field"


def build_financial_export(source: pd.DataFrame, calculations: pd.DataFrame) -> pd.DataFrame:
    """Append calculated columns to the matching source rows, without collisions.

    Strict positional row alignment is intentional: row IDs may be duplicated.
    This function raises on row-count mismatch rather than writing a misleading CSV.
    """
    if len(source) != len(calculations):
        raise ValueError("Source and calculation row counts differ; export stopped.")
    if not calculations.columns.is_unique:
        raise ValueError("Calculation column names must be unique.")
    if not source.columns.is_unique:
        raise ValueError("Source column names must be unique for an unambiguous export.")
    existing = {str(col).casefold() for col in source.columns}
    converted = {}
    for name in calculations.columns:
        base = "BI_" + _safe_header(name)
        target = base
        suffix = 2
        while target.casefold() in existing:
            target = f"{base}_{suffix}"
            suffix += 1
        existing.add(target.casefold())
        converted[name] = target
    return pd.concat([
        source.reset_index(drop=True).copy(),
        calculations.reset_index(drop=True).rename(columns=converted).copy(),
    ], axis=1)


def excel_safe_csv(data: pd.DataFrame) -> bytes:
    """Export UTF-8 with BOM; guard leading spreadsheet-formula text.

    Numeric types remain numeric, including negative figures. Suspicious text
    beginning with =, +, -, @ (even after spaces/tabs/newlines) is prefixed with
    a literal apostrophe. This is an intentional export-only representation.
    """
    output = data.copy(deep=True)
    output.columns = [
        "'" + str(col) if str(col).lstrip().startswith(("=", "+", "-", "@")) else col
        for col in output.columns
    ]
    for col in output.columns:
        series = output[col]
        if pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
            def escape_formula(value):
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    return "'" + value
                return value
            output[col] = series.map(escape_formula)
    return output.to_csv(index=False).encode("utf-8-sig")
