"""Reusable, escaped navigation mastheads for Python BI Studio.

Works with the existing Streamlit sidebar and does not mutate session state.
The human-facing branding is original; it is not an imitation of another firm.
"""
from __future__ import annotations
from html import escape
from typing import Any

PAGES = {
    "Home": ("PLATFORM OVERVIEW", "Python BI Studio", "Analytics, assurance and evidence-led decisions in one workspace."),
    "Data Workspace": ("DATA OPERATIONS", "Data Workspace", "Explore, prepare and analyse the same active source with a controlled workflow."),
    "Dashboard": ("EXECUTIVE ANALYTICS", "Executive Dashboard", "Decision-ready charts, audited financial measures and reporting."),
    "Investment Intelligence": ("INVESTMENT RESEARCH", "Investment Intelligence", "Business cash-flow scenarios and historical market risk — separate evidence streams."),
}


def masthead_html(page: str, dataset_name: str, row_count: int | None) -> str:
    """Render a small, safe masthead. No raw records or client code enter the DOM."""
    kicker, title, description = PAGES.get(page, ("PLATFORM", "Python BI Studio", "Workspace"))
    safe_name = escape(str(dataset_name)[:120], quote=True)
    scope = "NO ACTIVE DATASET" if row_count is None else f"ACTIVE DATASET · {row_count:,} RECORDS"
    return (
        '<div class="bi-page-masthead" role="region" aria-label="Workspace context">'
        f'<div class="bi-page-kicker">{escape(kicker)}</div>'
        '<div class="bi-page-masthead-inner">'
        '<div class="bi-page-ident">'
        f'<h1 class="bi-page-title">{escape(title)}</h1>'
        f'<p class="bi-page-description">{escape(description)}</p>'
        '</div>'
        '<div class="bi-dataset-pill" aria-label="Active dataset">'
        '<span class="bi-live-dot" aria-hidden="true"></span>'
        f'<div><span class="bi-dataset-state">{scope}</span>'
        f'<span class="bi-dataset-name">{safe_name}</span></div>'
        '</div></div></div>'
    )


def render_page_masthead(page: str, dataset_name: str, active_data: Any) -> None:
    import streamlit as st
    rows = len(active_data) if hasattr(active_data, "columns") and hasattr(active_data, "__len__") else None
    st.markdown(masthead_html(page, dataset_name, rows), unsafe_allow_html=True)
