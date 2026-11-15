"""Optional local benchmark and synthetic CSV generator for Python BI Studio.

Runs independently of Streamlit; does not touch data/business/ or stored_datasets/.
Usage:
    python modules/benchmark_explorer.py --rows 10000
    python modules/benchmark_explorer.py --rows 500000 --emit-test-csv --output outputs/benchmark_artifacts/results.json
Then upload outputs/benchmark_artifacts/synthetic_explorer_500000.csv through Data Workspace.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from full_dataset_engine import MAX_EXPORT_ROWS, explore_dataset


def make_synthetic(n: int) -> pd.DataFrame:
    """Deterministic 14-field fake commerce data with a sentinel in the LAST row."""
    if not 1 <= n <= 1_000_000:
        raise ValueError("Synthetic row count must be 1–1,000,000.")
    r = np.arange(n)
    quantity = (r % 9) + 1
    unit = (r % 90) + 25
    sales = (unit * quantity).astype("float64")
    cost = sales * 0.73
    data = pd.DataFrame({
        "TransactionID": [f"T{i:07d}" for i in r],
        "Date": pd.Timestamp("2025-01-01") + pd.to_timedelta(r % 700, unit="D"),
        "ProductID": [f"P{i % 175:03d}" for i in r],
        "Product": np.take(["Laptop", "Monitor", "Mouse", "Keyboard", "Headphones"], r % 5),
        "CustomerID": [f"C{i % 28000:05d}" for i in r],
        "Customer Name": [f"Synthetic Customer {i % 28000}" for i in r],
        "Sales": sales,
        "Quantity": quantity,
        "City": np.take(["Delhi", "Mumbai", "Bengaluru", "Pune", "Chennai"], r % 5),
        "Region": np.take(["North", "West", "South", "East"], r % 4),
        "Unit Cost": cost / quantity,
        "Total Cost": cost,
        "Profit": sales - cost,
        "Profit Margin (%)": np.full(n, 27.0),
    })
    data.loc[n - 1, "Customer Name"] = f"SPECIAL-ROW-{n - 1:09d}"
    return data


def run_benchmark(n: int, *, emit_test_csv: bool = False, output: str | None = None) -> dict:
    start = perf_counter()
    source = make_synthetic(n)
    create_seconds = perf_counter() - start
    sentinel = f"SPECIAL-ROW-{n - 1:09d}"
    begin = perf_counter()
    preview, export, meta = explore_dataset(
        source, source.columns.tolist(), search_text=sentinel,
        preview_limit=20,
    )
    scan_seconds = perf_counter() - begin
    if meta.matched_rows != 1 or preview["Customer Name"].iloc[0] != sentinel:
        raise AssertionError("The full-dataset search failed to locate the last record.")
    begin = perf_counter()
    common_preview, common_export, common_meta = explore_dataset(
        source, ["Product", "Sales"], search_text="Laptop", preview_limit=100,
    )
    group_search_seconds = perf_counter() - begin
    if common_meta.matched_rows == 0 or len(common_preview) > 100:
        raise AssertionError("Common-item search/preview was incorrect.")
    if common_meta.matched_rows > MAX_EXPORT_ROWS and not common_meta.export_truncated:
        raise AssertionError("Truncated export was not disclosed.")
    csv_location = None
    if emit_test_csv:
        destination = Path("outputs/benchmark_artifacts")
        destination.mkdir(parents=True,exist_ok=True)
        path = destination / f"synthetic_explorer_{n}.csv"
        source.to_csv(path, index=False)
        csv_location = str(path)
    report = {
        "scope": "Isolated Pandas full-dataset Explorer operations; Streamlit upload NOT benchmarked here",
        "synthetic_records": n, "columns": len(source.columns),
        "sentinel": sentinel, "last_record_found": True,
        "common_search_matching_records": common_meta.matched_rows,
        "common_search_preview_rows": len(common_preview),
        "common_search_export_rows": len(common_export),
        "common_search_export_truncated": common_meta.export_truncated,
        "source_memory_mib": round(source.memory_usage(index=True, deep=True).sum() / (1024 ** 2), 3),
        "generation_seconds": round(create_seconds, 4),
        "last_row_search_seconds": round(scan_seconds, 4),
        "common_search_seconds": round(group_search_seconds, 4),
        "synthetic_csv": csv_location,
    }
    if output:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--emit-test-csv", action="store_true")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    print(json.dumps(run_benchmark(args.rows, emit_test_csv=args.emit_test_csv, output=args.output), indent=2))
