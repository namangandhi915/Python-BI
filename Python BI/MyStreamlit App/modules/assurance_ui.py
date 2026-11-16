"""One collapsed Home assurance panel; no new top-level navigation or server actions."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from assurance_contracts import inspect_dataset, readiness_notes, MAX_SAMPLE
from audit_exports import excel_safe_csv


def render_assurance_home(active: pd.DataFrame | None) -> None:
    with st.expander('Platform assurance · dataset health', expanded=False):
        st.caption('Checks help interpret the current source. A sampled result does not certify all records or the complete website.')
        if not isinstance(active, pd.DataFrame):
            st.info('Activate a dataset in Dataset Library to inspect its schema and quality.')
            return
        if active.columns.empty:
            st.warning('The source has no columns.')
            return
        preview_options = [10, 20, 50, 100, 500, 1000, 10000, 100000, 500000, 1000000]
        current_preview = st.session_state.get('explorer_preview_setting', 100)
        chosen_preview = st.selectbox('Maximum Explorer preview rows', preview_options, index=preview_options.index(current_preview), key='explorer_preview_widget', help='Large previews can slow your browser.')
        st.session_state['explorer_preview_setting'] = chosen_preview
        limit = st.selectbox('Quality diagnostic sample size', [100, 500, 2000, 5000, 10000, 100000, 500000, 1000000], index=2, key='assurance_sample_rows')
        exact = st.checkbox('Run exact missing-value and duplicate counts on the entire active source (optional)',
                            value=False, key='assurance_exact_source_scan')
        try:
            summary, profile = inspect_dataset(active, sample_size=int(limit), exact=exact)
        except (ValueError, TypeError) as error:
            st.error(f'Unable to inspect active data: {error}')
            return
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Source records', f'{summary["rows"]:,}')
        c2.metric('Source columns', f'{summary["columns"]:,}')
        c3.metric('Checked missing cells', f'{summary["checked_missing_cells"]:,}')
        c4.metric('Checked duplicate rows', f'{summary["checked_duplicate_rows"]:,}')
        label = ('Exact scan over all rows' if exact else f'Deterministic sample of {summary["sample_rows"]:,} rows')
        st.caption(f'{label}. Missing and duplicate results are limited to this stated scope. Source records are not changed.')
        st.dataframe(profile, width='stretch', hide_index=True)
        for note in readiness_notes(summary):
            st.caption(note)
        st.download_button('Download data-quality summary (no source row values)',
                           data=excel_safe_csv(profile),file_name='python_bi_assurance_profile.csv',
                           mime='text/csv', key='assurance_profile_export')
