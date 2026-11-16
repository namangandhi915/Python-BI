"""Streamlit Section 06 — on-demand, audited executive report downloads."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from audit_exports import excel_safe_csv
from report_engine import build_executive_report
from report_bundle import build_report_archive


def render_executive_report(
    filtered: pd.DataFrame,
    calculations: pd.DataFrame,
    totals: dict,
    *,
    dataset_name: str,
    mapping: dict[str, str],
    filter_summary: str,
) -> None:
    with st.expander("06  ·  Executive report centre", expanded=False):
        st.caption(
            "Create a standalone, print-ready executive HTML report from the same filtered records "
            "and commercial mapping used above. CSV reports include all category/period rows. "
            "No transactions or files leave your computer."
        )
        categories = [c for c in filtered.columns if
                      pd.api.types.is_object_dtype(filtered[c])
                      or pd.api.types.is_string_dtype(filtered[c])
                      or isinstance(filtered[c].dtype, pd.CategoricalDtype)]
        dates = [c for c in filtered.columns if
                 "date" in str(c).casefold() or "time" in str(c).casefold()
                 or pd.api.types.is_datetime64_any_dtype(filtered[c])]
        a, b = st.columns(2)
        with a:
            group = st.selectbox(
                "Report category", ["No category breakdown"] + categories,
                index=(["No category breakdown"] + categories).index("Product")
                if "Product" in categories else 0, key="exec_report_group",
            )
            frequency = st.selectbox(
                "Report calendar periods", ["Monthly", "Quarterly", "Yearly"],
                key="exec_report_frequency",
            )
        with b:
            date = st.selectbox(
                "Report date field", ["No time breakdown"] + dates,
                index=(["No time breakdown"] + dates).index("Date")
                if "Date" in dates else 0, key="exec_report_date",
            )
            unit = st.text_input(
                "Currency / reporting unit", value="Not specified",
                max_chars=40, help="A label only; figures are not converted between currencies.",
                key="exec_report_unit",
            )
        st.caption(
            "The printed report shows aggregate results only, not customer-level transaction records. "
            "Transaction-level calculations are available in Commercial Intelligence. "
            "Use Chrome/Edge Print → Save as PDF after opening the downloaded HTML file."
        )
        if not st.button("Generate executive report", key="exec_report_generate", type="primary"):
            return
        try:
            bundle = build_executive_report(
                filtered, calculations, totals,
                dataset_name=dataset_name,
                category=None if group == "No category breakdown" else group,
                date_column=None if date == "No time breakdown" else date,
                period=frequency,
                field_mapping=mapping,
                filter_notes=filter_summary,
                currency_label=unit.strip() or "Not specified",
            )
        except (ValueError, TypeError, OverflowError) as exc:
            st.error(f"Report generation stopped: {exc}")
            return
        st.success(f"Report ready for {bundle['matching_rows']:,} filtered transactions.")
        # One downloadable package with self-verifiable aggregate reports.
        try:
            archive = build_report_archive(
                bundle, dataset_name=dataset_name,
                filter_context=filter_summary,
                period=frequency,
                category=None if group == "No category breakdown" else group,
                currency=unit.strip() or "Not specified",
            )
        except (ValueError, TypeError, OverflowError) as exc:
            st.warning(f"Complete report pack unavailable: {exc}")
        else:
            st.download_button(
                "Download complete executive report pack (ZIP)",
                data=archive, file_name="python_bi_executive_report_pack.zip",
                mime="application/zip", key="exec_report_pack_zip", on_click="ignore",
            )
            st.caption(
                "Pack includes the executive HTML, Excel-friendly aggregate CSVs, "
                "README and SHA-256 integrity manifest. No raw transaction rows are included; "
                "selected category labels may contain sensitive identifiers."
            )
        st.download_button(
            "Download executive report (HTML)", data=bundle["html"],
            file_name="python_bi_executive_report.html", mime="text/html",
            key="exec_report_html_download", on_click="ignore",
        )
        left, middle, right = st.columns(3)
        with left:
            st.download_button(
                "Download KPI summary (CSV)", excel_safe_csv(bundle["summary"]),
                file_name="python_bi_report_kpis.csv", mime="text/csv",
                key="exec_report_kpi_csv", on_click="ignore",
            )
        with middle:
            if not bundle["categories"].empty:
                st.download_button(
                    "Download category report (CSV)", excel_safe_csv(bundle["categories"]),
                    file_name="python_bi_report_categories.csv", mime="text/csv",
                    key="exec_report_category_csv", on_click="ignore",
                )
        with right:
            if not bundle["periods"].empty:
                st.download_button(
                    "Download period report (CSV)", excel_safe_csv(bundle["periods"]),
                    file_name="python_bi_report_periods.csv", mime="text/csv",
                    key="exec_report_period_csv", on_click="ignore",
                )
        st.dataframe(bundle["summary"], width="stretch", hide_index=True)
        st.caption("Report totals are checked against the same underlying row-level commercial calculations.")
