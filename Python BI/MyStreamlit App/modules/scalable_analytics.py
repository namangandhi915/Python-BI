"""Bounded, testable chart data preparation for Python BI Studio.

Every chart calculation uses the SAME ordered Dashboard-filtered records as its
financial mapping. Plot-ready output is bounded; source frames are never mutated.
Missing/non-finite chart measure values are counted and excluded, not made zero.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

PERIODS = {"Monthly": "M", "Quarterly": "Q", "Yearly": "Y"}
MAX_GROUPS = 50
MAX_PERIODS = 250
MAX_SCATTER_POINTS = 1_000_000


def numeric_measure_options(source: pd.DataFrame, calculations: pd.DataFrame) -> list[str]:
    """Clearly label original numeric fields vs. computed financial fields."""
    _check_frames(source, calculations)
    source_options = [f"Source: {c}" for c in source.select_dtypes(include="number").columns]
    finance_options = [f"Calculated: {c}" for c in calculations.select_dtypes(include="number").columns]
    return finance_options + source_options


def is_ratio_measure(name: str) -> bool:
    """A sum of source percentages/margins is generally not a meaningful metric."""
    lowered = str(name).casefold()
    return any(token in lowered for token in ("%", "margin", "ratio", "roi", "rate", "percentage"))


def _check_frames(source: pd.DataFrame, calculations: pd.DataFrame) -> None:
    if len(source) != len(calculations):
        raise ValueError("Source records and calculated financial rows do not align.")
    if not source.columns.is_unique or not calculations.columns.is_unique:
        raise ValueError("Duplicate column names must be resolved before charting.")


def _value_series(source: pd.DataFrame, calculations: pd.DataFrame, metric: str) -> tuple[pd.Series, np.ndarray]:
    _check_frames(source, calculations)
    if metric.startswith("Source: "):
        name = metric[len("Source: "):]
        table = source
    elif metric.startswith("Calculated: "):
        name = metric[len("Calculated: "):]
        table = calculations
    else:
        raise ValueError("Select a valid source or calculated measure.")
    if name not in table.columns:
        raise ValueError(f"Measure '{name}' is not in the available dataset.")
    if not pd.api.types.is_numeric_dtype(table[name]):
        raise ValueError("The selected measure is not numeric.")
    # Reset indices before joining series; duplicated business record IDs are valid.
    values = pd.to_numeric(table[name], errors="coerce").reset_index(drop=True)
    arr = values.to_numpy(dtype="float64", na_value=np.nan)
    valid = np.isfinite(arr)
    return values, valid


def _category_values(source: pd.DataFrame, category: str) -> pd.Series:
    if category not in source.columns:
        raise ValueError(f"Unknown category field: {category}")
    return source[category].reset_index(drop=True).astype("string").fillna("(Missing)")


def category_chart_data(
    source: pd.DataFrame, calculations: pd.DataFrame, category: str,
    metric: str, aggregation: str = "Sum", top_n: int = 12,
    direction: str = "Highest", with_remainder: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Return bounded categories and audit metadata; donut remainder reconciles sums."""
    if aggregation not in ("Sum", "Average"):
        raise ValueError("Choose Sum or Average.")
    if direction not in ("Highest", "Lowest"):
        raise ValueError("Choose Highest or Lowest.")
    if not 1 <= int(top_n) <= MAX_GROUPS:
        raise ValueError(f"Top N must be between 1 and {MAX_GROUPS}.")
    if aggregation == "Sum" and is_ratio_measure(metric):
        raise ValueError("Summing percentages or ratios is misleading. Choose Average, or chart the underlying amounts.")
    if with_remainder and aggregation != "Sum":
        raise ValueError("A remainder can only be combined with Sum, not Average.")
    if with_remainder and direction != "Highest":
        raise ValueError("Donut charts require highest-first selection.")
    values, finite = _value_series(source, calculations, metric)
    valid_count = int(finite.sum())
    meta = {"included_rows": valid_count, "excluded_measure_rows": int((~finite).sum()),
            "all_groups": 0, "shown_groups": 0, "truncated_groups": 0}
    if not valid_count:
        return pd.DataFrame(columns=["Category", "Value", "Records"]), meta
    frame = pd.DataFrame({"Category": _category_values(source, category).loc[finite].to_numpy(),
                          "Value": values.loc[finite].to_numpy(dtype=float)})
    grouped = frame.groupby("Category", dropna=False, observed=True)["Value"].agg(
        Value="sum" if aggregation == "Sum" else "mean", Records="size"
    ).reset_index()
    grouped = grouped.sort_values(["Value", "Category"],
                                  ascending=[direction == "Lowest", True], kind="stable")
    meta["all_groups"] = len(grouped)
    top = grouped.head(int(top_n)).copy()
    tail = grouped.iloc[int(top_n):]
    if with_remainder:
        if (grouped["Value"] < 0).any():
            raise ValueError("A donut is not suitable when the selected groups have negative values. Use a bar chart.")
        if len(tail):
            other_name = f"Other categories ({len(tail)})"
            if other_name in grouped["Category"].tolist():
                other_name = f"Remaining groups ({len(tail)})"
            top = pd.concat([top, pd.DataFrame({
                "Category": [other_name], "Value": [float(tail["Value"].sum())],
                "Records": [int(tail["Records"].sum())],
            })], ignore_index=True)
    meta["shown_groups"] = len(top)
    meta["truncated_groups"] = len(tail)
    meta["complete_metric_total"] = float(frame["Value"].sum()) if aggregation == "Sum" else None
    return top.reset_index(drop=True), meta


def time_chart_data(
    source: pd.DataFrame, calculations: pd.DataFrame, date_column: str,
    metric: str, cadence: str = "Monthly", aggregation: str = "Sum",
) -> tuple[pd.DataFrame, dict]:
    if date_column not in source.columns:
        raise ValueError("The selected date field is missing.")
    if cadence not in PERIODS:
        raise ValueError("Choose Monthly, Quarterly or Yearly.")
    if aggregation not in ("Sum", "Average"):
        raise ValueError("Choose Sum or Average.")
    if aggregation == "Sum" and is_ratio_measure(metric):
        raise ValueError("Do not sum a percentage or ratio. Use Average or the underlying amounts.")
    values, finite = _value_series(source, calculations, metric)
    parsed = pd.to_datetime(source[date_column].reset_index(drop=True), format="mixed", errors="coerce")
    accepted = parsed.notna().to_numpy() & finite
    meta = {"included_rows": int(accepted.sum()), "excluded_invalid_dates": int(parsed.isna().sum()),
            "excluded_measure_rows": int((~finite).sum()), "periods": 0}
    if not accepted.any():
        return pd.DataFrame(columns=["Period", "Value", "Records"]), meta
    try:
        indexed = parsed.loc[accepted].dt.to_period(PERIODS[cadence])
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("Dates cannot be grouped; check inconsistent time zones and formats.") from error
    frame = pd.DataFrame({"Period": indexed.to_numpy(),
                          "Value": values.loc[accepted].to_numpy(dtype=float)})
    grouped = frame.groupby("Period", observed=True, sort=True)["Value"].agg(
        Value="sum" if aggregation == "Sum" else "mean", Records="size"
    ).reset_index()
    if len(grouped) > MAX_PERIODS:
        raise ValueError(f"{len(grouped):,} time points exceed the {MAX_PERIODS} point chart limit. Choose a coarser period.")
    grouped["Period"] = grouped["Period"].astype(str)
    meta["periods"] = len(grouped)
    return grouped, meta


def scatter_chart_data(
    source: pd.DataFrame, calculations: pd.DataFrame,
    x_metric: str, y_metric: str, max_points: int = 1_000,
) -> tuple[pd.DataFrame, dict]:
    if not 1 <= int(max_points) <= MAX_SCATTER_POINTS:
        raise ValueError(f"Sample size must be 1–{MAX_SCATTER_POINTS:,} points.")
    x, good_x = _value_series(source, calculations, x_metric)
    y, good_y = _value_series(source, calculations, y_metric)
    accepted = good_x & good_y
    full_count = int(accepted.sum())
    frame = pd.DataFrame({"X": x.loc[accepted].to_numpy(dtype=float),
                          "Y": y.loc[accepted].to_numpy(dtype=float)})
    if len(frame) > max_points:
        frame = frame.sample(n=int(max_points), random_state=42).sort_index()
    return frame.reset_index(drop=True), {"valid_rows": full_count,
                                          "excluded_rows": int((~accepted).sum()),
                                          "charted_rows": len(frame),
                                          "is_sample": len(frame) < full_count}


def histogram_chart_data(
    source: pd.DataFrame, calculations: pd.DataFrame, metric: str,
    bins: int = 20,
) -> tuple[pd.DataFrame, dict]:
    if not 5 <= int(bins) <= 80:
        raise ValueError("Histogram bins must be between 5 and 80.")
    values, finite = _value_series(source, calculations, metric)
    good = values.loc[finite].to_numpy(dtype=float)
    meta = {"included_rows": len(good), "excluded_measure_rows": int((~finite).sum())}
    if not len(good):
        return pd.DataFrame(columns=["Bin midpoint", "Bin lower", "Bin upper", "Records"]), meta
    counts, edges = np.histogram(good, bins=int(bins))
    frame = pd.DataFrame({"Bin midpoint": (edges[:-1] + edges[1:]) / 2,
                          "Bin lower": edges[:-1], "Bin upper": edges[1:],
                          "Records": counts.astype(int)})
    assert int(frame["Records"].sum()) == len(good)
    return frame, meta
