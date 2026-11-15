"""Professional, full-source Explorer: controls grouped and previews bounded.

Importing this module does not read, persist or mutate any source dataset.
"""
from __future__ import annotations

import hashlib
import numpy as np
import pandas as pd
import streamlit as st

from audit_exports import excel_safe_csv
from full_dataset_engine import (
    DEFAULT_CHUNK_SIZE, MAX_EXPORT_ROWS, MAX_PREVIEW_ROWS,
    explore_dataset, safe_preview,
)


def render_explorer_workspace(source: pd.DataFrame) -> None:
    """Replace the old first-N-rows-only search without changing the Library."""
    if source.columns.empty:
        st.warning("This dataset has no columns to explore.")
        return
    if not source.columns.is_unique or any(not isinstance(col, str) for col in source.columns):
        st.error("Column names must be unique text values before exploration.")
        return

    # Scope widget state to the column schema to prevent invalid stale selections
    # when users activate a different Dataset Library file.
    schema = repr((tuple(source.columns), tuple(str(t) for t in source.dtypes)))
    schema_id = hashlib.sha256(schema.encode("utf-8")).hexdigest()[:12]
    def widget_key(suffix: str) -> str:
        return f"explorer_v2_{schema_id}_{suffix}"

    st.caption(
        "Searches, category filters and numeric filters examine ALL active records. "
        "Preview and CSV sizes are limited separately to protect responsiveness."
    )
    overview1, overview2, overview3 = st.columns(3)
    overview1.metric("Source records", f"{len(source):,}")
    overview2.metric("Source columns", f"{len(source.columns):,}")
    overview3.metric("Preview cap", f"{MAX_PREVIEW_ROWS:,}")

    with st.expander("01 · Fields and search", expanded=True):
        selected = st.multiselect(
            "Columns to explore", options=source.columns.tolist(),
            default=source.columns.tolist(), key=widget_key("columns")
        )
        query = st.text_input(
            "Search all records (case-insensitive, literal)",
            placeholder="Example: Laptop, Delhi, T001 or 2026-01",
            key=widget_key("query"),
        )
        preview_limit = st.selectbox(
            "Maximum preview rows", [10, 20, 50, 100, 500, 1000],
            index=3, key=widget_key("preview_rows"),
        )

    if not selected:
        st.info("Choose at least one column to explore.")
        return

    category_column = None
    selected_values = None
    numeric_column = None
    numeric_min = None
    numeric_max = None
    sort_column = None
    ascending = True

    with st.expander("02 · Optional filters and sorting", expanded=False):
        category_choice = st.selectbox(
            "Category column", ["No category filter", *selected],
            key=widget_key("category_column"),
        )
        if category_choice != "No category filter":
            category_column = category_choice
            # Show up to 100 most common options. High-cardinality values can
            # still be found via the full-dataset text search.
            values = source[category_column].value_counts(dropna=True).head(100)
            category_options = [str(v) for v in values.index]
            selected_values = st.multiselect(
                "Category values (leave empty for all)", category_options,
                default=[], key=widget_key("category_values"),
            )
            if source[category_column].nunique(dropna=True) > len(category_options):
                st.caption(
                    "The selector shows only the 100 most common categories. "
                    "Use text search to find other category values across all rows."
                )
            if not selected_values:
                # An empty widget means the filter is not active.
                category_column = None
                selected_values = None

        numeric_choices = [col for col in selected if pd.api.types.is_numeric_dtype(source[col])]
        numeric_choice = st.selectbox(
            "Numeric column", ["No numeric filter", *numeric_choices],
            key=widget_key("numeric_column"),
        )
        if numeric_choice != "No numeric filter":
            candidates = pd.to_numeric(source[numeric_choice], errors="coerce")
            candidates = candidates.replace([np.inf, -np.inf], np.nan).dropna()
            if not candidates.empty:
                numeric_column = numeric_choice
                numeric_min = st.number_input(
                    "Minimum (inclusive)", value=float(candidates.min()),
                    key=widget_key("min"),
                )
                numeric_max = st.number_input(
                    "Maximum (inclusive)", value=float(candidates.max()),
                    key=widget_key("max"),
                )
            else:
                st.info("The chosen numeric field has no finite values.")

        sort_choice = st.selectbox(
            "Sort matching records", ["No sorting", *selected],
            key=widget_key("sort_column"),
        )
        if sort_choice != "No sorting":
            sort_column = sort_choice
            ascending = st.radio(
                "Sort direction", ["Ascending", "Descending"],
                horizontal=True, key=widget_key("sort_direction"),
            ) == "Ascending"
            if len(source) >= 100_000:
                st.caption("Sorting large matching sets may take additional time and memory.")

    if numeric_column and numeric_min > numeric_max:
        st.warning("The minimum numeric value must not exceed the maximum.")
        return

    try:
        preview, export_rows, info = explore_dataset(
            source, selected, search_text=query,
            category_column=category_column, category_values=selected_values,
            numeric_column=numeric_column, minimum=numeric_min, maximum=numeric_max,
            sort_column=sort_column, ascending=ascending,
            preview_limit=preview_limit, export_limit=MAX_EXPORT_ROWS,
            chunk_size=DEFAULT_CHUNK_SIZE,
        )
    except (ValueError, TypeError, OverflowError) as error:
        st.error(f"Unable to apply the selected Explorer controls: {error}")
        return

    st.markdown("**Matching records**")
    stat1, stat2, stat3 = st.columns(3)
    stat1.metric("Full-dataset matches", f"{info.matched_rows:,}")
    stat2.metric("Records shown", f"{info.shown_rows:,}")
    stat3.metric("Filter processing", f"{info.total_seconds:.3f} s")
    st.dataframe(safe_preview(preview), width="stretch", hide_index=True)
    st.caption(
        f"Results are computed across {info.source_rows:,} source records, "
        f"with a separate preview limit of {preview_limit:,}. "
        "The complete active dataset is not changed."
    )

    with st.expander("03 · Download and field quality", expanded=False):
        if info.export_truncated:
            st.warning(
                f"{info.matched_rows:,} records match, but the download is capped "
                f"at {info.exported_rows:,} rows. It is a PARTIAL export. "
                "Refine your filters to export all matching rows."
            )
        else:
            st.caption(f"This export contains all {info.exported_rows:,} matching rows.")
        if info.exported_rows:
            st.download_button(
                "Download filtered CSV",
                excel_safe_csv(export_rows),
                file_name="python_bi_full_dataset_explorer.csv",
                mime="text/csv", key=widget_key("csv"),
            )
        else:
            st.info("No matching records are available to export.")

        st.caption("Source field summary. Exact missing counts are optional on large files.")
        check_exact = st.checkbox(
            "Calculate exact missing and duplicate counts",
            value=len(source) <= 25_000,
            key=widget_key("exact_quality"),
        )
        field_info = pd.DataFrame({
            "Column": [str(col) for col in source.columns],
            "Data type": [str(dtype) for dtype in source.dtypes],
        })
        if check_exact:
            field_info["Missing cells"] = source.isna().sum().to_numpy(dtype=int)
            st.metric("Exact duplicate records", f"{source.duplicated().sum():,}")
        st.dataframe(field_info, width="stretch", hide_index=True)
