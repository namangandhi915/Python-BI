"""Concise, optional Executive Dashboard comparison and readiness panels."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from audit_exports import excel_safe_csv
from data_readiness import dataset_profile
from period_comparison import available_periods, compare_periods


def _field_options(data: pd.DataFrame) -> list[str]:
    return [col for col in data.columns if
            "date" in str(col).casefold() or "time" in str(col).casefold()
            or pd.api.types.is_datetime64_any_dtype(data[col])]


def render_comparison_panel(filtered: pd.DataFrame, calculations: pd.DataFrame) -> None:
    with st.expander("03  ·  Compare financial periods", expanded=False):
        st.caption(
            "Compare two calendar months, quarters or years within the same Dashboard filters. "
            "Dates excluded from the comparison do not affect the Dashboard's main KPIs."
        )
        if not st.checkbox("Calculate financial period comparison", key="cmp_run"):
            return
        dates = _field_options(filtered)
        if not dates:
            st.info("This dataset has no identified date or timestamp field.")
            return
        col1, col2 = st.columns(2)
        with col1:
            date_col = st.selectbox("Date field", dates,
                                    index=dates.index("Date") if "Date" in dates else 0,
                                    key="cmp_date")
        with col2:
            cadence = st.selectbox("Calendar periods", ["Monthly", "Quarterly", "Yearly"],
                                    key="cmp_cadence")
        try:
            periods, invalid_count = available_periods(filtered, date_col, cadence)
            if invalid_count:
                st.warning(f"{invalid_count:,} records have invalid/missing dates; only the comparison excludes them.")
            if len(periods) < 2:
                st.info("Two different observed periods are required. The current dataset or filters include fewer than two.")
                return
            start, end = st.columns(2)
            with start:
                earlier = st.selectbox("Earlier period", periods, index=len(periods) - 2,
                                       key=f"cmp_earlier_{cadence}")
            with end:
                later = st.selectbox("Later period", periods, index=len(periods) - 1,
                                     key=f"cmp_later_{cadence}")
            options = ["No category breakdown"] + [col for col in filtered.columns
                if pd.api.types.is_string_dtype(filtered[col])
                or pd.api.types.is_object_dtype(filtered[col])
                or isinstance(filtered[col].dtype, pd.CategoricalDtype)]
            cat = st.selectbox("Optional category breakdown", options,
                               index=options.index("Product") if "Product" in options else 0,
                               key="cmp_category")
            summary, breakdown, audit = compare_periods(
                filtered, calculations, date_col, cadence, earlier, later,
                None if cat == "No category breakdown" else cat,
            )
            if not audit["periods_are_adjacent"]:
                st.warning("Periods are not adjacent: the displayed change is between the two selected periods, not a consecutive-period growth rate.")
            st.caption(
                f"Compared {audit['earlier_rows']:,} earlier and {audit['later_rows']:,} later records; "
                f"{audit['excluded_other_period_rows']:,} valid-dated records are from other periods."
            )
            st.dataframe(summary, width="stretch", hide_index=True)
            st.download_button("Export period comparison", excel_safe_csv(summary),
                               file_name="python_bi_period_comparison.csv", mime="text/csv",
                               key="cmp_summary_export")
            if not breakdown.empty:
                st.markdown("#### Category movements")
                st.dataframe(breakdown.head(100), width="stretch", hide_index=True)
                top = breakdown.head(12)
                if not top.empty:
                    chart = top.melt(id_vars="Category", value_vars=["Earlier Revenue", "Later Revenue"],
                                     var_name="Period", value_name="Revenue")
                    st.plotly_chart(px.bar(chart, x="Category", y="Revenue", color="Period",
                                           barmode="group", title="Net revenue by category and period"),
                                    width="stretch")
                st.download_button("Export full category comparison", excel_safe_csv(breakdown),
                                   file_name="python_bi_period_category_comparison.csv", mime="text/csv",
                                   key="cmp_category_export")
                st.caption("Full category report is exported even when only the first 100 groups appear in the table.")
        except (ValueError, TypeError, OverflowError) as error:
            st.warning(f"Unable to compare the selected periods: {error}")


def render_readiness_panel(source: pd.DataFrame) -> None:
    with st.expander("06  ·  Dataset scale and readiness", expanded=False):
        st.caption(
            "This diagnostic describes the entire active source dataset, not just Dashboard-filtered records. "
            "Profiles are sampled for responsiveness; an optional exact missing-value scan is available."
        )
        sample_limit = st.select_slider("Sample rows for diagnostics", options=[100, 500, 1_000, 5_000, 10_000, 25_000],
                                        value=5_000, key="readiness_sample_limit")
        exact_scan = st.checkbox("Calculate exact missing counts for every source column",
                                 value=(len(source) <= 5_000), key="readiness_exact_missing")
        try:
            info, table, preview = dataset_profile(source, sample_limit=sample_limit,
                                                   exact_missing_scan=exact_scan)
        except (ValueError, TypeError) as error:
            st.warning(f"Unable to profile this dataset: {error}")
            return
        tiles = st.columns(4)
        tiles[0].metric("Source records", f"{info['source_rows']:,}")
        tiles[1].metric("Source columns", f"{info['source_columns']:,}")
        tiles[2].metric("Sampled records", f"{info['sample_rows']:,}")
        tiles[3].metric("Missing cells" if exact_scan else "Missing in sample",
                        f"{info['exact_missing_cells'] if exact_scan else info['sample_missing_cells']:,}")
        st.caption(
            f"Sample duplicate rows: {info['sample_duplicate_rows']:,} (not a full-source count). "
            f"Shallow DataFrame storage: {info['source_shallow_memory_mb']:.2f} MiB. "
            f"Approximate total memory from sample: {info['estimated_deep_memory_mb']:.2f} MiB "
            "(rough estimate, not a benchmark)."
        )
        st.dataframe(table, width="stretch", hide_index=True)
        st.download_button("Export data-readiness profile", excel_safe_csv(table),
                           file_name="python_bi_data_readiness.csv", mime="text/csv",
                           key="readiness_export")
        st.dataframe(preview.head(50), width="stretch")
        st.caption(
            "The preview shows up to 50 reproducibly sampled rows. The application still loads the complete dataset "
            "into memory; these controls do not guarantee performance on 500,000+ rows."
        )
