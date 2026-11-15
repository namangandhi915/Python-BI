"""One collapsed Home-only production-readiness panel; not a fifth navigation page."""
from __future__ import annotations
from pathlib import Path
import streamlit as st
from release_evidence import build_report, evidence_zip


def render_operations_home() -> None:
    with st.expander("Release readiness · privacy & deployment", expanded=False):
        st.caption("This application is ready for local testing, not yet for public multi-user deployment. This preflight does not access source record values.")
        report = build_report(Path(__file__).resolve().parents[1])
        c1, c2, c3 = st.columns(3)
        c1.metric("Automated controls passed", report["counts"]["PASS"])
        c2.metric("Public deployment blockers", report["counts"]["BLOCKED"])
        c3.metric("Checks for review", report["counts"]["MANUAL"] + report["counts"]["REVIEW"])
        st.warning("Public deployment remains blocked: shared Dataset Library storage needs authentication, per-user isolation and durable persistence.")
        st.dataframe(report["checks"], width="stretch", hide_index=True)
        st.download_button(
            "Download release-readiness evidence ZIP",
            data=evidence_zip(report), file_name="python_bi_release_readiness.zip",
            mime="application/zip", key="operations_release_evidence",
        )
        st.caption("The ZIP contains only issue descriptions and status summaries. No uploaded datasets, customer rows or secrets are included.")
