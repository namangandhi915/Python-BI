"""Optional Executive Dashboard Section 10 — portfolio and Pareto insights."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st
from audit_exports import excel_safe_csv
from portfolio_analytics import build_category_concentration


def render_portfolio_panel(source: pd.DataFrame, calculations: pd.DataFrame, totals: dict) -> None:
    with st.expander("07  ·  Revenue concentration and category mix", expanded=False):
        st.caption(
            "Analyze category revenue distribution after all Executive Dashboard filters. "
            "This does not estimate industry-wide market share."
        )
        fields = [c for c in source.columns if (
            pd.api.types.is_object_dtype(source[c]) or pd.api.types.is_string_dtype(source[c])
            or isinstance(source[c].dtype, pd.CategoricalDtype)
        )]
        if not fields:
            st.info("This dataset has no category or text field for revenue concentration.")
            return
        choice = st.selectbox(
            "Group revenue by", fields,
            index=fields.index("Product") if "Product" in fields else 0,
            key="ex_mix_category",
        )
        if not st.checkbox("Calculate category mix", value=False, key="ex_mix_run"):
            st.caption("Opt in to run the category group-by; no source data will be modified.")
            return
        try:
            result = build_category_concentration(source, calculations, totals, choice)
        except (TypeError, ValueError, OverflowError) as exc:
            st.warning(f"Category mix not available: {exc}")
            return
        metrics, groups = result["metrics"], result["groups"]
        a, b, c = st.columns(3)
        a.metric("Categories", f"{metrics['category_count']:,}")
        b.metric("Top category", metrics["top_category"])
        if metrics["concentration_available"]:
            c.metric("Top 3 revenue share", f"{metrics['top_three_share_pct']:.2f}%")
            d, e = st.columns(2)
            d.metric("Categories reaching 80% revenue", metrics["categories_to_80_pct"])
            e.metric("Within-dataset concentration index", f"{metrics['concentration_index']:,.0f}")
        else:
            c.metric("Revenue-share statistics", "Unavailable")
        for note in result["notes"]:
            st.caption(note)
        if metrics["concentration_available"]:
            top = groups.head(15)
            fig = px.bar(top, x="Category", y="Net Revenue", title="Top categories by net revenue")
            fig.update_layout(margin=dict(l=15, r=15, t=45, b=35))
            st.plotly_chart(fig, width="stretch")
        st.dataframe(groups.head(200), width="stretch", hide_index=True)
        st.download_button(
            "Download complete category-mix audit (CSV)",
            data=excel_safe_csv(groups),
            file_name="python_bi_category_mix.csv", mime="text/csv",
            key="ex_mix_download", on_click="ignore",
        )
        st.caption("The CSV includes all categories; the table previews at most 200 groups.")
