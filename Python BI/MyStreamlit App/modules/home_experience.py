"""Python BI Studio — coherent enterprise Home experience.

The visual hierarchy is inspired by general corporate design-system principles,
not a copied external website. All dynamic content is HTML-escaped.
"""
from __future__ import annotations

from html import escape
import pandas as pd
import streamlit as st


def render_home() -> None:
    active = st.session_state.get("uploaded_df")
    if not isinstance(active, pd.DataFrame):
        active = None
    name = escape(str(st.session_state.get("uploaded_name", "No dataset activated")), quote=True)
    source_status = "DATASET CONNECTED" if active is not None else "READY FOR DATA"
    st.markdown(f"""
    <section class="bi-home-hero">
      <div class="bi-hero-copy">
        <div class="bi-eyebrow"><span class="bi-eyebrow-dot"></span> PYTHON BI STUDIO / ENTERPRISE ANALYTICS</div>
        <h2 class="bi-home-title">Clarity in every decision.<br><span>Confidence in every number.</span></h2>
        <p class="bi-home-lead">Explore your data, validate its quality, understand business performance and build evidence-led decisions in one professional workspace.</p>
        <div class="bi-home-state"><span class="bi-state-indicator"></span> {source_status} <span class="bi-home-divider"></span> {name}</div>
      </div>
      <div class="bi-hero-art" aria-hidden="true">
        <div class="bi-art-title">PERFORMANCE SIGNAL</div>
        <svg viewBox="0 0 360 170" preserveAspectRatio="xMidYMid meet" role="presentation">
          <path d="M2 141H358M2 107H358M2 73H358M2 39H358" stroke="#DCE7F4" stroke-width="1"/>
          <path d="M7 139 L57 115 L110 128 L165 73 L217 83 L278 38 L353 19 L353 160 L7 160Z" fill="#2878E5" fill-opacity=".10"/>
          <path d="M7 139 L57 115 L110 128 L165 73 L217 83 L278 38 L353 19" fill="none" stroke="#2878E5" stroke-width="3.3" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="278" cy="38" r="5.5" fill="#2878E5" stroke="white" stroke-width="3"/>
        </svg>
        <div class="bi-art-foot"><span>REVENUE INTELLIGENCE</span><span>DATA-LED</span></div>
      </div>
    </section>
    """, unsafe_allow_html=True)
    st.markdown("<div class='bi-section-eyebrow'>YOUR WORKSPACE</div>", unsafe_allow_html=True)
    st.markdown("<h3 class='bi-home-section-heading'>A connected intelligence workflow</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="bi-home-grid">
      <article class="bi-home-feature"><span class="bi-feature-index">01 / DATA</span><h4>Data Workspace</h4>
        <p>Profile, filter, clean and validate source datasets. Inspect missing values and prepare reusable analysis.</p>
        <span class="bi-feature-state">AVAILABLE</span></article>
      <article class="bi-home-feature"><span class="bi-feature-index">02 / ANALYTICS</span><h4>Executive Dashboard</h4>
        <p>Review reconciled KPIs, financial trends, profitability and configurable interactive charts.</p>
        <span class="bi-feature-state">AVAILABLE</span></article>
      <article class="bi-home-feature"><span class="bi-feature-index">03 / PLANNING</span><h4>Commercial Intelligence</h4>
        <p>Map financial fields, model break-even scenarios and examine assumptions without inventing missing costs.</p>
        <span class="bi-feature-state">AVAILABLE</span></article>
      <article class="bi-home-feature"><span class="bi-feature-index">04 / STRATEGY</span><h4>Investment Intelligence</h4>
        <p>Explore user-defined business cash-flow scenarios and historical financial-market risks in separate modes.</p>
        <span class="bi-feature-state">FOUNDATION AVAILABLE</span></article>
    </div>
    """, unsafe_allow_html=True)
    if active is None:
        st.info("Begin by opening Data Workspace and uploading a CSV or Excel file, or activate a saved dataset in Dataset Library.")
    else:
        k1, k2, k3 = st.columns(3)
        k1.metric("Active source records", f"{len(active):,}")
        k2.metric("Source columns", f"{len(active.columns):,}")
        k3.metric("Active data status", "Connected")
        st.caption("Source counts describe the original active dataset, not Dashboard-filtered rows.")
    st.caption("Open Data Workspace or Dashboard from the left sidebar to continue. Reports are available under Executive Dashboard → Section 06.")
