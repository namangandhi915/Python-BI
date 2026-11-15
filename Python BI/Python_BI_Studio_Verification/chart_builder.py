"""Executive Dashboard chart studio: chart controls and bounded rendering.

Uses the already-filtered records and calculations; no new dataset upload,
financial remapping or navigation page is required.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from audit_exports import excel_safe_csv
from scalable_analytics import (
    category_chart_data, histogram_chart_data, is_ratio_measure,
    numeric_measure_options, scatter_chart_data, time_chart_data,
)
from performance_lab import benchmark_grouping


FINANCE_ACCENT = ["#2878E5", "#142B4A", "#45A08B", "#7F90AA", "#D19C52"]


def _choose_index(options: list[str], words: tuple[str, ...]) -> int:
    for word in words:
        for index, option in enumerate(options):
            if option.casefold() == word.casefold():
                return index
    return 0


def _finish(fig):
    fig.update_layout(
        font=dict(family="IBM Plex Sans, Segoe UI, sans-serif", color="#142B4A"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=45, b=30),
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E6EDF6", zerolinecolor="#A8B9CE")
    return fig


def _metrics(source: pd.DataFrame, calculations: pd.DataFrame):
    metrics = numeric_measure_options(source, calculations)
    preferred = ("Calculated: Net Revenue", "Source: Sales", "Calculated: Gross Revenue")
    return metrics, _choose_index(metrics, preferred)


def _aggregation(metric: str, key: str):
    if is_ratio_measure(metric):
        st.caption("Percentages and ratios cannot be summed. The chart uses an unweighted average; for financial margins, compare underlying revenue and profit instead.")
        return "Average"
    return st.selectbox("Aggregation", ["Sum", "Average"], key=key)


def _notice(meta: dict) -> None:
    excluded = meta.get("excluded_measure_rows", 0)
    if excluded:
        st.warning(f"{excluded:,} rows with missing or non-finite chart values were excluded. They were not converted to zero.")
    date_excluded = meta.get("excluded_invalid_dates", 0)
    if date_excluded:
        st.warning(f"{date_excluded:,} rows with missing or invalid dates were excluded from this chart.")


def render_chart_studio(filtered: pd.DataFrame, calculations: pd.DataFrame) -> None:
    with st.expander("07  ·  Interactive chart studio", expanded=False):
        st.caption(
            "Change chart type, measures and dimensions here—without switching to the legacy Dashboard. "
            "The chart uses exactly the Executive Dashboard filters and mapped financial calculations."
        )
        if not st.checkbox(
            'Load interactive Chart Studio',
            value=False,
            key='studio_load_on_demand',
        ):
            st.caption(
                'Enable this option to display charts '
                'and chart-data downloads.'
            )
            return

        try:
            measures, default_index = _metrics(filtered, calculations)
        except ValueError as exc:
            st.warning(f"Cannot open chart studio: {exc}")
            return
        if not measures:
            st.info("No numeric fields are available to chart.")
            return
        kind = st.selectbox(
            "Chart type", ["Bar", "Line", "Area", "Donut", "Scatter", "Histogram"],
            key="studio_chart_type",
        )
        categories = [col for col in filtered.columns if
                      pd.api.types.is_object_dtype(filtered[col])
                      or pd.api.types.is_string_dtype(filtered[col])
                      or isinstance(filtered[col].dtype, pd.CategoricalDtype)]
        date_fields = [col for col in filtered.columns if
                       "date" in str(col).casefold() or "time" in str(col).casefold()
                       or pd.api.types.is_datetime64_any_dtype(filtered[col])]
        left, right = st.columns(2)
        with left:
            metric = st.selectbox("Measure", measures, index=default_index, key="studio_metric")
        if kind in ("Bar", "Donut"):
            if not categories:
                st.info("Add a categorical field to use bar or donut charts.")
                return
            with right:
                category = st.selectbox(
                    "Category / X-axis", categories,
                    index=_choose_index(categories, ("Product", "Region", "City")),
                    key="studio_category",
                )
            c1, c2, c3 = st.columns(3)
            with c1:
                agg = "Sum" if kind == "Donut" else _aggregation(metric, "studio_bar_aggregation")
            with c2:
                top_n = st.select_slider("Categories to display", [5, 10, 12, 20, 30, 50], value=12,
                                         key="studio_top_n")
            with c3:
                direction = "Highest" if kind == "Donut" else st.selectbox(
                    "Rank order", ["Highest", "Lowest"], key="studio_rank_order",
                )
            try:
                chart, meta = category_chart_data(
                    filtered, calculations, category, metric, agg, top_n, direction,
                    with_remainder=(kind == "Donut"),
                )
            except ValueError as exc:
                st.warning(str(exc))
                return
            _notice(meta)
            if chart.empty:
                st.info("No valid chart values are available.")
                return
            if kind == "Donut":
                if float(chart["Value"].sum()) <= 0:
                    st.info("A donut chart requires a positive total. Use a bar chart instead.")
                    return
                fig = px.pie(chart, names="Category", values="Value", hole=0.48,
                             color_discrete_sequence=FINANCE_ACCENT,
                             title=f"{metric} by {category}")
            else:
                fig = px.bar(chart, x="Category", y="Value", title=f"{agg} · {metric}",
                             color_discrete_sequence=FINANCE_ACCENT)
            st.plotly_chart(_finish(fig), width="stretch")
            st.caption(
                f"{meta['included_rows']:,} valid records, {meta['all_groups']:,} categories. "
                + ("Remaining categories are grouped into Other to preserve the sum." if kind == "Donut" and meta['truncated_groups'] else
                   f"Chart displays {meta['shown_groups']:,} categories; {meta['truncated_groups']:,} not shown. "
                   "Exports contain the displayed result only.")
            )
            _download(chart, "python_bi_custom_category_chart.csv", "studio_cat_export")

        elif kind in ("Line", "Area"):
            if not date_fields:
                st.info("Select a dataset containing a date/timestamp column for time-series charts.")
                return
            with right:
                date_col = st.selectbox("Date / X-axis", date_fields,
                                        index=_choose_index(date_fields, ("Date", "Order Date")),
                                        key="studio_date_column")
            a, b = st.columns(2)
            with a:
                cadence = st.selectbox("Period", ["Monthly", "Quarterly", "Yearly"],
                                        key="studio_time_period")
            with b:
                agg = _aggregation(metric, "studio_time_aggregation")
            try:
                chart, meta = time_chart_data(filtered, calculations, date_col, metric, cadence, agg)
            except ValueError as exc:
                st.warning(str(exc))
                return
            _notice(meta)
            if chart.empty:
                st.info("No valid dated observations were found.")
                return
            fig = (px.line(chart, x="Period", y="Value", markers=True,
                           title=f"{metric} by {cadence.lower()} period", color_discrete_sequence=FINANCE_ACCENT)
                   if kind == "Line" else
                   px.area(chart, x="Period", y="Value", title=f"{metric} by {cadence.lower()} period",
                           color_discrete_sequence=FINANCE_ACCENT))
            st.plotly_chart(_finish(fig), width="stretch")
            st.caption(f"Showing {meta['periods']:,} periods from {meta['included_rows']:,} valid rows. Empty calendar periods are not invented as zero.")
            _download(chart, "python_bi_custom_time_chart.csv", "studio_time_export")

        elif kind == "Scatter":
            with right:
                y_metric = st.selectbox("Y-axis measure", measures,
                                        index=min(default_index + 1, len(measures) - 1),
                                        key="studio_scatter_y")
            size = st.select_slider("Maximum plotted points", [100, 500, 1_000, 2_500, 5_000],
                                    value=1_000, key="studio_scatter_limit")
            try:
                chart, meta = scatter_chart_data(filtered, calculations, metric, y_metric, size)
            except ValueError as exc:
                st.warning(str(exc))
                return
            if chart.empty:
                st.info("No valid X/Y pairs were found.")
                return
            fig = px.scatter(chart, x="X", y="Y", title=f"{metric} versus {y_metric}",
                             color_discrete_sequence=FINANCE_ACCENT)
            st.plotly_chart(_finish(fig), width="stretch")
            st.caption(
                f"{meta['charted_rows']:,} points displayed from {meta['valid_rows']:,} complete numeric pairs. "
                + ("This is a reproducible sample, not every source record." if meta['is_sample'] else "Every valid pair is shown.")
            )
            if meta['excluded_rows']:
                st.warning(f"{meta['excluded_rows']:,} rows excluded due to missing/non-finite X or Y values.")
            _download(chart, "python_bi_custom_scatter_chart.csv", "studio_scatter_export")

        else:  # Histogram
            with right:
                bins = st.slider("Number of histogram bins", min_value=5, max_value=80,
                                 value=20, step=5, key="studio_histogram_bins")
            try:
                chart, meta = histogram_chart_data(filtered, calculations, metric, bins)
            except ValueError as exc:
                st.warning(str(exc))
                return
            _notice(meta)
            if chart.empty:
                st.info("No valid numeric values were found.")
                return
            fig = px.bar(chart, x="Bin midpoint", y="Records", title=f"Distribution of {metric}",
                         color_discrete_sequence=FINANCE_ACCENT)
            st.plotly_chart(_finish(fig), width="stretch")
            st.caption(f"Histogram bin counts cover all {meta['included_rows']:,} valid records; individual records are not rendered.")
            _download(chart, "python_bi_custom_histogram.csv", "studio_histogram_export")


def _download(frame: pd.DataFrame, file_name: str, key: str) -> None:
    st.download_button("Download this chart's data", data=excel_safe_csv(frame),
                       file_name=file_name, mime="text/csv", key=key)


def render_performance_lab(source: pd.DataFrame) -> None:
    with st.expander("08  ·  Performance lab (bounded sample)", expanded=False):
        st.caption(
            "Run an optional local grouping diagnostic on a reproducible sample (maximum 50,000 rows). "
            "This is NOT a benchmark of 500,000-record uploads, full-source charts, or the complete website."
        )
        categories = [col for col in source.columns if
                      pd.api.types.is_object_dtype(source[col])
                      or pd.api.types.is_string_dtype(source[col])
                      or isinstance(source[col].dtype, pd.CategoricalDtype)]
        numeric = source.select_dtypes(include="number").columns.tolist()
        if not categories or not numeric:
            st.info("A categorical field and a numeric field are required for this diagnostic.")
            return
        a, b, c = st.columns(3)
        with a:
            category = st.selectbox("Group by", categories,
                                     index=_choose_index(categories, ("Product", "Region", "City")),
                                     key="studio_bench_category")
        with b:
            metric = st.selectbox("Numeric value", numeric,
                                  index=_choose_index(numeric, ("Sales", "Revenue")),
                                  key="studio_bench_metric")
        with c:
            sample_size = st.select_slider("Max sampled records", [100, 1_000, 5_000, 10_000, 25_000, 50_000],
                                           value=10_000, key="studio_bench_sample")
        if st.button("Run sample grouping diagnostic", key="studio_run_benchmark"):
            try:
                result, leaders = benchmark_grouping(source, category, metric, sample_size)
            except ValueError as exc:
                st.warning(str(exc))
                return
            b1, b2, b3 = st.columns(3)
            b1.metric("Sample rows", f"{result['sample_rows']:,}")
            b2.metric("Elapsed (ms)", f"{result['elapsed_ms']:,.2f}")
            b3.metric("Groups", f"{result['group_count']:,}")
            if result["excluded_nonnumeric"]:
                st.warning(f"{result['excluded_nonnumeric']:,} invalid numeric rows excluded from this diagnostic.")
            st.caption(
                f"Sample memory: {result['sample_memory_mib']:.3f} MiB. "
                "Time includes the sampled two-column preparation and grouping. "
                "Your hardware, data types and number of categories affect this measurement."
            )
            st.dataframe(leaders, width="stretch", hide_index=True)
