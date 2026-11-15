"""Optional, local synthetic Pandas benchmark. Does NOT test Streamlit upload speed.

Examples:
    python modules/benchmark_phase3.py --rows 10000
    python modules/benchmark_phase3.py --rows 500000 --output outputs/benchmark_artifacts/performance_results.json
"""
from __future__ import annotations

import argparse
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

MIN_ROWS = 1000
MAX_ROWS = 500000


def benchmark(rows: int = 10000) -> dict:
    if isinstance(rows, bool) or not isinstance(rows, int) or not MIN_ROWS <= rows <= MAX_ROWS:
        raise ValueError(f"Row count must be an integer from {MIN_ROWS:,} to {MAX_ROWS:,}.")
    rng = np.random.default_rng(2026)
    start = perf_counter()
    frame = pd.DataFrame({
        "Product": pd.Categorical.from_codes(rng.integers(0, 100, rows),
                                             categories=[f"Product_{x:03d}" for x in range(100)]),
        "Region": pd.Categorical.from_codes(rng.integers(0, 12, rows),
                                            categories=[f"Region_{x:02d}" for x in range(12)]),
        "Sales": rng.integers(100, 40000, rows, dtype=np.int64),
        "Cost": rng.integers(50, 25000, rows, dtype=np.int64),
        "Month": pd.Categorical.from_codes(rng.integers(0, 12, rows),
                                            categories=[f"2026-{m:02d}" for m in range(1, 13)]),
    })
    generate_sec = perf_counter() - start
    memory_mib = frame.memory_usage(index=True, deep=True).sum() / 1024**2

    start = perf_counter()
    selected = frame.loc[(frame["Sales"] >= 15000) & frame["Region"].isin(["Region_01", "Region_02"])].copy()
    filter_sec = perf_counter() - start

    start = perf_counter()
    group = (selected.groupby("Product", observed=True, as_index=False)
             .agg(Net_Revenue=("Sales", "sum"), Mapped_Costs=("Cost", "sum")))
    group_sec = perf_counter() - start
    if (int(group["Net_Revenue"].sum()) != int(selected["Sales"].sum())
            or int(group["Mapped_Costs"].sum()) != int(selected["Cost"].sum())):
        raise AssertionError("Benchmark grouping totals did not reconcile.")

    start = perf_counter()
    # Bounded chart-style payload; never serialize 500k source records by default.
    csv_bytes = group.head(100).to_csv(index=False).encode("utf-8")
    export_sec = perf_counter() - start
    results = {
        "scope": "Isolated local synthetic Pandas operations only; NOT Streamlit upload/UI benchmark",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Deterministic synthetic data; no user dataset read or uploaded",
        "rows": rows,
        "columns": int(len(frame.columns)),
        "selected_rows": int(len(selected)),
        "group_count": int(len(group)),
        "dataframe_memory_mib": round(float(memory_mib), 3),
        "timings_seconds": {
            "generate": round(generate_sec, 6),
            "filter": round(filter_sec, 6),
            "group": round(group_sec, 6),
            "bounded_csv": round(export_sec, 6),
        },
        "reconciled": True,
        "csv_preview_bytes": len(csv_bytes),
        "environment": {"python": platform.python_version(), "pandas": pd.__version__},
    }
    if not all(math.isfinite(t) and t >= 0 for t in results["timings_seconds"].values()):
        raise AssertionError("Invalid benchmark measurements.")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark synthetic data operations safely, locally.")
    parser.add_argument("--rows", type=int, default=10000,
                        help="Synthetic rows between 1,000 and 500,000 (default 10,000).")
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional JSON file to save results (no source rows included).")
    args = parser.parse_args()
    try:
        results = benchmark(args.rows)
        output = json.dumps(results, indent=2, allow_nan=False)
        print(output)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
            print(f"Saved benchmark report: {args.output}")
    except (ValueError, OSError, AssertionError) as exc:
        parser.exit(1, f"Benchmark failed: {exc}\n")

if __name__ == "__main__":
    main()
