
import streamlit as st
import pandas as pd
import plotly.express as px

import json
import hashlib
from pathlib import Path
import sys
from uuid import uuid4

MODULES_DIR = Path(__file__).resolve().parent / "modules"
if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))

from commerce_engine import render_commercial_intelligence, calculate_commercial_metrics
from quality_engine import quality_overview, quality_table, missing_records
from executive_dashboard import render_executive_dashboard
from home_experience import render_home
from planning_workspace import render_planning_workspace
from investment_workspace import render_investment_intelligence
from explorer_workspace import render_explorer_workspace
from assurance_ui import render_assurance_home
from design_system import render_page_masthead
from operations_ui import render_operations_home
from local_file_guard import validate_upload, safe_stored_path
from schema_aware_dashboard import assess_legacy, render_safe_details
from ui_runtime_metrics import tracked_render, instrument

# Capture selected server-side view performance only when opted in; retain
# exactly the same Streamlit page call sites and previous functionality.
render_home = instrument("Home", render_home)
render_assurance_home = instrument("Home assurance", render_assurance_home)
render_operations_home = instrument("Home readiness", render_operations_home)
render_explorer_workspace = instrument("Explorer", render_explorer_workspace)
render_commercial_intelligence = instrument("Commercial Intelligence", render_commercial_intelligence)
render_planning_workspace = instrument("Business Planning", render_planning_workspace)
render_investment_intelligence = instrument("Investment Intelligence", render_investment_intelligence)
render_executive_dashboard = instrument("Executive Dashboard", render_executive_dashboard)

st.set_page_config(
    page_title="Python BI Studio",
    page_icon="📊",
    layout="wide"
)

# --------------------------------------------------
# PHASE 2 - PERMANENT DATASET STORAGE
# --------------------------------------------------

STORAGE_DIR = Path(__file__).resolve().parent / "stored_datasets"
ACTIVE_FILE = STORAGE_DIR / "active_dataset.json"



def save_active_dataset(uploaded_file):
    """Save uploads without duplicating identical files."""

    file_info = validate_upload(uploaded_file)
    extension = file_info["extension"]

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    file_bytes = uploaded_file.getvalue()
    file_hash = file_info["sha256"]

    stored_name = None

    # Search for an identical saved file.
    for existing_file in STORAGE_DIR.iterdir():
        if (
            existing_file.is_file()
            and not existing_file.is_symlink()
            and existing_file.suffix.lower() == extension
        ):
            existing_hash = hashlib.sha256(
                existing_file.read_bytes()
            ).hexdigest()

            if existing_hash == file_hash:
                stored_name = existing_file.name
                break

    # Save only when no identical file exists.
    if stored_name is None:
        stored_name = f"{uuid4().hex}{extension}"
        stored_path = safe_stored_path(STORAGE_DIR, stored_name)
        stored_path.write_bytes(file_bytes)

    metadata = {
        "name": uploaded_file.name,
        "stored_name": stored_name,
        "hash": file_hash
    }

    temporary_file = STORAGE_DIR / "active_dataset.tmp"

    temporary_file.write_text(
        json.dumps(metadata),
        encoding="utf-8"
    )

    temporary_file.replace(ACTIVE_FILE)


def restore_active_dataset():
    """Restore the last saved dataset into session state."""

    if "uploaded_df" in st.session_state:
        return

    if not ACTIVE_FILE.exists():
        return

    try:
        metadata = json.loads(
            ACTIVE_FILE.read_text(encoding="utf-8")
        )

        stored_name = metadata["stored_name"]
        stored_path = safe_stored_path(STORAGE_DIR, stored_name, must_exist=True)
        saved_hash = metadata.get("hash")
        if saved_hash and hashlib.sha256(stored_path.read_bytes()).hexdigest() != saved_hash:
            raise ValueError("Saved dataset failed its SHA-256 integrity check.")

        if stored_path.suffix.lower() == ".csv":
            restored_df = pd.read_csv(stored_path)
        else:
            restored_df = pd.read_excel(stored_path)

        st.session_state["uploaded_df"] = restored_df.copy()
        st.session_state["uploaded_name"] = metadata["name"]

    except (OSError, ValueError, KeyError, ImportError) as error:
        st.warning(f"Unable to restore saved dataset: {error}")


def load_dataset_labels():
    """Load custom names for saved datasets."""

    labels_file = STORAGE_DIR / "dataset_labels.json"

    if not labels_file.exists():
        return {}

    try:
        return json.loads(
            labels_file.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return {}


def save_dataset_label(stored_name, display_name):
    """Save a readable dataset name."""

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    labels_file = STORAGE_DIR / "dataset_labels.json"
    labels = load_dataset_labels()

    labels[stored_name] = display_name.strip()

    labels_file.write_text(
        json.dumps(labels, indent=4),
        encoding="utf-8"
    )

restore_active_dataset()

def list_saved_datasets():
    """Find datasets stored by Python BI Studio."""

    if not STORAGE_DIR.exists():
        return []

    saved_files = []

    for file_path in STORAGE_DIR.iterdir():
        if file_path.is_file() and not file_path.is_symlink() and file_path.suffix.lower() in (".csv", ".xlsx"):
            try:
                saved_files.append(safe_stored_path(STORAGE_DIR, file_path.name))
            except ValueError:
                continue

    return sorted(
        saved_files,
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )


def get_dataset_information(stored_name):
    """Return information about a saved dataset."""

    file_path = safe_stored_path(STORAGE_DIR, stored_name)

    if not file_path.is_file():
        return None

    from datetime import datetime

    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    modified_time = datetime.fromtimestamp(
        file_path.stat().st_mtime
    ).strftime("%d %b %Y, %I:%M %p")

    return {
        "file_type": file_path.suffix.upper().replace(".", ""),
        "file_size_mb": file_size_mb,
        "modified_time": modified_time
    }


def delete_saved_dataset(stored_name):
    """Delete a non-active saved dataset safely."""

    # Only permit files registered in the library.
    valid_names = {
        path.name for path in list_saved_datasets()
    }

    if stored_name not in valid_names:
        raise ValueError("Dataset is not available.")

    # Protect the active dataset.
    if ACTIVE_FILE.exists():
        active_metadata = json.loads(
            ACTIVE_FILE.read_text(encoding="utf-8")
        )

        if active_metadata.get("stored_name") == stored_name:
            raise ValueError(
                "The active dataset cannot be deleted. "
                "Activate another dataset first."
            )

    stored_path = safe_stored_path(STORAGE_DIR, stored_name, must_exist=True)
    stored_path.unlink()

    # Remove its saved display name.
    labels_file = STORAGE_DIR / "dataset_labels.json"
    labels = load_dataset_labels()

    if stored_name in labels:
        del labels[stored_name]

        labels_file.write_text(
            json.dumps(labels, indent=4),
            encoding="utf-8"
        )


# --------------------------------------------------
# PYTHON BI STUDIO - CORPORATE LIGHT THEME
# --------------------------------------------------

# Unified style tokens live in bi_theme.css (not duplicated inline).
THEME_FILE = Path(__file__).resolve().parent / "assets" / "bi_theme.css"
if THEME_FILE.exists():
    st.markdown(
        "<style>" + THEME_FILE.read_text(encoding="utf-8") + "</style>",
        unsafe_allow_html=True,
    )



# --------------------------------------------------
# PYTHON BI STUDIO - PROFESSIONAL BRANDING
# --------------------------------------------------


st.sidebar.markdown(
    """
    
<div class="bi-brand">
    <div class="bi-brand-icon">BI</div>
    <div class="bi-brand-text">
        <div class="bi-brand-name">Python BI</div>
        <div class="bi-brand-name">Studio</div>
        <div class="bi-brand-subtitle">
            ENTERPRISE ANALYTICS
        </div>
    </div>
</div>

    """,
    unsafe_allow_html=True
)

st.sidebar.divider()

page = st.sidebar.radio(
    "Go to:",
    ["Home", "Data Workspace", "Dashboard", "Investment Intelligence"],
    label_visibility="collapsed",
)
render_page_masthead(
    page,
    st.session_state.get("uploaded_name", "No active dataset"),
    st.session_state.get("uploaded_df"),
)

# PHASE 2.5 - DATASET LIBRARY

st.sidebar.divider()
st.sidebar.markdown("### Dataset Library")

saved_datasets = list_saved_datasets()
dataset_labels = load_dataset_labels()

if saved_datasets:
    dataset_options = [
        path.name for path in saved_datasets
    ]

   
   
    selected_dataset = st.sidebar.selectbox(
        "Select a saved dataset",
        options=dataset_options,
        format_func=lambda name: dataset_labels.get(
            name,
            f"Dataset {name[:8]}"
        ),
        key="library_selection"
    )


else:
    selected_dataset = None
    st.sidebar.info("No saved datasets available.")

# DATASET DISPLAY NAME MANAGEMENT

if selected_dataset is not None:

    new_dataset_name = st.sidebar.text_input(
        "Dataset display name",
        value=dataset_labels.get(selected_dataset, ""),
        key=f"rename_{selected_dataset}"
    )

    if st.sidebar.button("Save Dataset Name"):
        if new_dataset_name.strip():
            save_dataset_label(
                selected_dataset,
                new_dataset_name
            )
            st.rerun()
        else:
            st.sidebar.warning(
                "Please enter a dataset name."
            )


# PHASE 2.5 - ACTIVATE SAVED DATASET

if selected_dataset is not None:

    if st.sidebar.button("Activate Selected Dataset"):

        selected_path = safe_stored_path(STORAGE_DIR, selected_dataset, must_exist=True)

        try:
            if selected_path.suffix.lower() == ".csv":
                selected_df = pd.read_csv(selected_path)
            else:
                selected_df = pd.read_excel(selected_path)

            # Remember the selected dataset permanently
            metadata = {
                "name": dataset_labels.get(selected_dataset, selected_dataset),
                "stored_name": selected_dataset,
                "hash": hashlib.sha256(
                    selected_path.read_bytes()
                ).hexdigest()
            }

            temporary_file = STORAGE_DIR / "active_dataset.tmp"

            temporary_file.write_text(
                json.dumps(metadata),
                encoding="utf-8"
            )

            temporary_file.replace(ACTIVE_FILE)

            # Update the shared dataset
            st.session_state["uploaded_df"] = selected_df.copy()
            st.session_state["uploaded_name"] = dataset_labels.get(
                selected_dataset, selected_dataset
            )
            
            st.session_state["uploader_version"] = (
                st.session_state.get("uploader_version", 0) + 1
            )

            st.rerun()

        except Exception as error:
            st.sidebar.error(
                f"Unable to activate dataset: {error}"
            )

# PHASE 2.5 - ACTIVE DATASET INFORMATION

if "uploaded_df" in st.session_state:

    st.sidebar.success(
        "Active Dataset: "
        + st.session_state.get(
            "uploaded_name",
            "Unnamed Dataset"
        )
    )

    st.sidebar.caption(
        f"Total Records: {len(st.session_state['uploaded_df']):,}"
    )

    st.sidebar.caption(
        f"Total Columns: {len(st.session_state['uploaded_df'].columns):,}"
    )


# PHASE 2.5C - SAVED DATASET DETAILS

if selected_dataset is not None:

    dataset_info = get_dataset_information(selected_dataset)

    if dataset_info is not None:

        with st.sidebar.expander("Dataset Information"):

            st.write(
                f"**File Type:** {dataset_info['file_type']}"
            )

            st.write(
                f"**File Size:** "
                f"{dataset_info['file_size_mb']:.2f} MB"
            )

            st.write(
                f"**Last Modified:** "
                f"{dataset_info['modified_time']}"
            )



# PHASE 2.5E - SAFE DATASET DELETION

if selected_dataset is not None:

    with st.sidebar.expander("Manage Saved Dataset"):

        st.warning(
            "Deleting a saved dataset cannot be undone."
        )

        confirm_delete = st.checkbox(
            "I confirm that I want to delete this dataset.",
            key=f"confirm_delete_{selected_dataset}"
        )

        if st.button(
            "Delete Selected Dataset",
            disabled=not confirm_delete,
            key="delete_dataset_button"
        ):
            try:
                delete_saved_dataset(selected_dataset)

                st.success("Dataset deleted successfully.")

                st.session_state.pop(
                    "library_selection",
                    None
                )

                st.rerun()

            except Exception as error:
                st.error(
                    f"Unable to delete dataset: {error}"
                )

if page == "Home":
    render_home()
    render_assurance_home(st.session_state.get("uploaded_df"))
    render_operations_home()

elif page == "Data Workspace":
    st.header("Data Workspace")
    st.caption(
        "Explore, prepare and calculate from the same active dataset. "
        "Use the workflow selector to keep tools organised."
    )
    workspace_mode = st.radio(
        "Workspace tools",
        ["Explore", "Prepare & Validate", "Commercial Intelligence"],
        horizontal=True,
        key="workspace_mode",
    )

    if workspace_mode == "Explore":
        st.subheader("Explore your data")

   
        uploaded_file = st.file_uploader(
            "Choose a CSV or Excel file",
            type=["csv", "xlsx"],
            key=f"explorer_uploader_{st.session_state.get('uploader_version', 0)}"
        )


    
        if uploaded_file is None and "uploaded_df" not in st.session_state:
            st.info("Upload a CSV or XLSX file to begin.")

        else:
            try:
                if uploaded_file is not None:
                    validate_upload(uploaded_file)
                    if uploaded_file.name.lower().endswith(".csv"):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)

                    st.session_state["uploaded_df"] = df.copy()
                    st.session_state["uploaded_name"] = uploaded_file.name
                
                    save_active_dataset(uploaded_file)

                else:
                    df = st.session_state["uploaded_df"].copy()

                # Phase 8 scalability track — search and filter the full dataset.
                # The source DataFrame and Dataset Library remain unmodified.
                st.success(
                    f"Active dataset: {st.session_state.get('uploaded_name', 'Dataset')}"
                )
                render_explorer_workspace(df)

            except Exception as e:
                st.error(
                    "Unable to explore this dataset. Please review the selected fields."
                )
                st.caption(f"Technical details: {e}")


    elif workspace_mode == "Prepare & Validate":
        st.subheader("Prepare and validate")

   
        uploaded_file = st.file_uploader(
            "Upload a CSV or Excel file",
            type=["csv", "xlsx"],
            key=f"cleaning_uploader_{st.session_state.get('uploader_version', 0)}"
        )

    
        if uploaded_file is not None or "uploaded_df" in st.session_state:
            try:
                if uploaded_file is not None:
                    validate_upload(uploaded_file)
                    if uploaded_file.name.lower().endswith(".csv"):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)

                    st.session_state["uploaded_df"] = df.copy()
                    st.session_state["uploaded_name"] = uploaded_file.name
                    save_active_dataset(uploaded_file)

                else:
                    df = st.session_state["uploaded_df"].copy()


                # Create a display-safe copy of the uploaded data
                df_display = df.copy()

                # Convert mixed object columns to consistent text for display
            
                for col in df_display.select_dtypes(include=["object"]).columns:
                    df_display[col] = (
                        df_display[col]
                        .astype("string")
                        .fillna("")
                    )


            
                st.success(
                    f"Active dataset: {st.session_state.get('uploaded_name', 'Dataset')}"
                )


                # Work on a copy so the original stays unchanged
                clean_df = df.copy()

                with st.expander('Data quality and missing values', expanded=True):
                    st.markdown("**Original data preview**")
                    st.dataframe(df_display.head(100), width="stretch")

                    st.markdown("**Data Quality Inspector**")
                    source_quality = quality_overview(df)
                    q1, q2, q3, q4 = st.columns(4)
                    q1.metric("Rows", f"{source_quality['rows']:,}")
                    q2.metric("Missing Cells", f"{source_quality['missing_cells']:,}")
                    q3.metric("Affected Rows", f"{source_quality['rows_with_missing']:,}")
                    q4.metric("Duplicates", f"{source_quality['duplicate_rows']:,}")
                    st.dataframe(quality_table(df), width="stretch", hide_index=True)
                    if source_quality["rows_with_missing"]:
                        missing_scope = st.selectbox(
                            "Find records with missing values",
                            ["Any column"] + df.columns.tolist(),
                            key="quality_missing_scope",
                        )
                        affected = missing_records(
                            df, None if missing_scope == "Any column" else missing_scope
                        )
                        st.caption(f"{len(affected):,} affected rows found")
                        st.dataframe(affected.head(100), width="stretch")
                        st.download_button(
                            "Export affected records", affected.to_csv(index=False).encode("utf-8"),
                            file_name="missing_records.csv", mime="text/csv",
                            key="quality_missing_export",
                        )
                    else:
                        st.success("No missing source values were detected.")

                with st.expander('Cleaning operations', expanded=False):
                    st.markdown("**Handle missing values**")
                    strategy = st.selectbox(
                        "How should missing values be handled?",
                        [
                            "Keep unchanged",
                            "Drop rows with missing values",
                            "Fill numeric gaps with mean",
                            "Fill numeric gaps with median"
                        ]
                    )

                    if strategy == "Drop rows with missing values":
                        clean_df = clean_df.dropna()

                    elif strategy == "Fill numeric gaps with mean":
                        numeric_cols = clean_df.select_dtypes(
                            include="number"
                        ).columns
                        for column in numeric_cols:
                            if clean_df[column].isna().any():
                                clean_df[column] = clean_df[column].fillna(
                                    clean_df[column].mean()
                                )

                    elif strategy == "Fill numeric gaps with median":
                        numeric_cols = clean_df.select_dtypes(
                            include="number"
                        ).columns
                        for column in numeric_cols:
                            if clean_df[column].isna().any():
                                clean_df[column] = clean_df[column].fillna(
                                    clean_df[column].median()
                                )

                    st.markdown("**Duplicate record management**")
                    remove_duplicates = st.checkbox(
                        "Remove duplicate rows from the cleaned copy"
                    )
                    if remove_duplicates:
                        clean_df = clean_df.drop_duplicates()

                    st.markdown("**Convert column types**")
                    column_to_convert = st.selectbox(
                        "Choose a column",
                        clean_df.columns.tolist()
                    )
                    conversion = st.selectbox(
                        "Convert the selected column to",
                        ["No conversion", "Text", "Numeric"]
                    )

                    if conversion == "Text":
                        clean_df[column_to_convert] = (
                            clean_df[column_to_convert].astype("string")
                        )
                    elif conversion == "Numeric":
                        try:
                            clean_df[column_to_convert] = pd.to_numeric(
                                clean_df[column_to_convert],
                                errors="raise"
                            )
                        except (ValueError, TypeError):
                            st.warning(
                                "This column contains values that cannot all "
                                "be converted to numbers. Choose another column "
                                "or keep its original type."
                            )


                with st.expander('Column comparison and missing-value details', expanded=False):
                    # PHASE 3.2.1 - TWO-COLUMN COMPARISON

                    st.markdown("**Compare two columns**")

                    enable_comparison = st.checkbox(
                        "Enable simultaneous two-column comparison",
                        key="prep_compare_enabled"
                    )

                    if enable_comparison:
                        compare_columns = st.multiselect(
                            "Select exactly two columns",
                            options=clean_df.columns.tolist(),
                            max_selections=2,
                            key="prep_compare_columns"
                        )

                        if len(compare_columns) == 2:
                            first_col, second_col = compare_columns

                            comparison_df = pd.DataFrame({
                                first_col: clean_df[first_col],
                                second_col: clean_df[second_col]
                            })

                            st.dataframe(
                                comparison_df.head(100),
                                width="stretch"
                            )

                            st.caption(
                                f"Comparing {first_col} and {second_col} "
                                f"across {len(comparison_df):,} records."
                            )
                        else:
                            st.info(
                                "Select two columns to compare."
                            )

                    # Unified missing-value counts and percentages appear in the Data Quality Inspector above.
                    # The results audit below reflects any changes made to clean_df.

                with st.expander('Text and numeric validation tools', expanded=False):
                    # PHASE 3.2.3 - WHITESPACE CLEANING

                    st.markdown("**Trim whitespace**")

                    text_columns = clean_df.select_dtypes(
                        include=["object", "string", "category"]
                    ).columns.tolist()

                    trim_columns = st.multiselect(
                        "Select text columns to trim",
                        options=text_columns,
                        key="prep_trim_columns"
                    )

                    if st.checkbox(
                        "Apply whitespace cleaning",
                        key="prep_trim_enabled"
                    ):
                        for column in trim_columns:
                            clean_df[column] = (
                                clean_df[column]
                                .astype("string")
                                .str.strip()
                            )

                        st.success(
                            "Whitespace cleaning applied "
                            "to the selected columns."
                        )

                    # PHASE 3.2.4 - TEXT STANDARDISATION

                    st.markdown("**Standardise text**")

                    standard_column = st.selectbox(
                        "Select text column",
                        options=["No selection"] + text_columns,
                        key="prep_standard_column"
                    )

                    standard_method = st.selectbox(
                        "Choose standardisation method",
                        options=[
                            "No change",
                            "Title Case",
                            "Uppercase",
                            "Lowercase"
                        ],
                        key="prep_standard_method"
                    )

                    if (
                        standard_column != "No selection"
                        and standard_method != "No change"
                    ):
                        text_series = clean_df[
                            standard_column
                        ].astype("string")

                        if standard_method == "Title Case":
                            clean_df[standard_column] = (
                                text_series.str.title()
                            )

                        elif standard_method == "Uppercase":
                            clean_df[standard_column] = (
                                text_series.str.upper()
                            )

                        elif standard_method == "Lowercase":
                            clean_df[standard_column] = (
                                text_series.str.lower()
                            )

                        st.success(
                            "Text standardisation applied."
                        )

                    # PHASE 3.2.5 - NUMERIC VALIDATION

                    st.markdown("**Validate numeric data**")

                    numeric_check_column = st.selectbox(
                        "Choose a column to validate as numeric",
                        options=["No selection"]
                        + clean_df.columns.tolist(),
                        key="prep_numeric_check"
                    )

                    if numeric_check_column != "No selection":
                        original_values = clean_df[
                            numeric_check_column
                        ]

                        converted_values = pd.to_numeric(
                            original_values,
                            errors="coerce"
                        )

                        invalid_mask = (
                            original_values.notna()
                            & converted_values.isna()
                        )

                        invalid_count = int(invalid_mask.sum())

                        st.metric(
                            "Invalid Numeric Values",
                            invalid_count
                        )

                        if invalid_count > 0:
                            st.dataframe(
                                clean_df.loc[
                                    invalid_mask,
                                    [numeric_check_column]
                                ].head(50),
                                width="stretch"
                            )

                    # PHASE 3.2.6 - OUTLIER ANALYSIS

                    st.markdown("**Investigate outliers**")

                    available_numeric = clean_df.select_dtypes(
                        include="number"
                    ).columns.tolist()

                    outlier_column = st.selectbox(
                        "Select a numeric column for outlier detection",
                        options=["No selection"] + available_numeric,
                        key="prep_outlier_column"
                    )

                    if outlier_column != "No selection":
                        values = pd.to_numeric(
                            clean_df[outlier_column],
                            errors="coerce"
                        )

                        q1 = values.quantile(0.25)
                        q3 = values.quantile(0.75)
                        iqr = q3 - q1

                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr

                        outlier_mask = (
                            (values < lower_bound)
                            | (values > upper_bound)
                        )

                        st.metric(
                            "Potential Outliers",
                            int(outlier_mask.sum())
                        )

                        st.dataframe(
                            clean_df.loc[outlier_mask].head(50),
                            width="stretch"
                        )

                    # PHASE 3.2.7 - DATE VALIDATION

                    st.markdown("**Validate timestamps**")

                    date_check_column = st.selectbox(
                        "Choose a date or timestamp column",
                        options=["No selection"]
                        + clean_df.columns.tolist(),
                        key="prep_date_check"
                    )

                    if date_check_column != "No selection":
                        source_dates = clean_df[
                            date_check_column
                        ]

                        parsed_dates = pd.to_datetime(
                            source_dates,
                            errors="coerce",
                            format="mixed"
                        )

                        invalid_dates = (
                            source_dates.notna()
                            & parsed_dates.isna()
                        )

                        st.metric(
                            "Invalid Date Values",
                            int(invalid_dates.sum())
                        )

                        if invalid_dates.any():
                            st.dataframe(
                                clean_df.loc[
                                    invalid_dates,
                                    [date_check_column]
                                ].head(50),
                                width="stretch"
                            )

                    # PHASE 3.2.8 - DATA QUALITY AUDIT

                    st.markdown("**Data quality audit**")

                    audit_col1, audit_col2, audit_col3 = st.columns(3)

                    audit_col1.metric(
                        "Prepared Records",
                        f"{len(clean_df):,}"
                    )

                    audit_col2.metric(
                        "Missing Cells",
                        int(clean_df.isna().sum().sum())
                    )

                    audit_col3.metric(
                        "Duplicate Records",
                        int(clean_df.duplicated().sum())
                    )

                    st.caption(
                        "Audit results describe the current "
                        "prepared dataset. The source dataset "
                        "remains unchanged."
                    )


                with st.expander('Results and export', expanded=True):
                    st.markdown("**Preparation results**")
                    before, after = st.columns(2)

                    with before:
                        st.write("**Before cleaning**")
                        st.metric("Rows", len(df))
                        st.metric(
                            "Missing Cells",
                            int(df.isna().sum().sum())
                        )
                        st.metric(
                            "Duplicate Rows",
                            int(df.duplicated().sum())
                        )

                    with after:
                        st.write("**After cleaning**")
                        st.metric("Rows", len(clean_df))
                        st.metric(
                            "Missing Cells",
                            int(clean_df.isna().sum().sum())
                        )
                        st.metric(
                            "Duplicate Rows",
                            int(clean_df.duplicated().sum())
                        )

                    st.dataframe(clean_df.head(100), width="stretch")

                    st.markdown("**Export prepared dataset**")
                    csv_data = clean_df.to_csv(index=False).encode("utf-8")

                    st.download_button(
                        label="Download cleaned CSV",
                        data=csv_data,
                        file_name="cleaned_data.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(
                    "Could not process this file. Please check that it is "
                    "a valid CSV or XLSX file."
                )
                st.caption(f"Technical details: {e}")



    else:
        if "uploaded_df" in st.session_state:
            current_data = st.session_state["uploaded_df"].copy()
            commercial_view = st.radio(
                "Commercial tools",
                ["Financial Performance", "Business Planning"],
                horizontal=True,
                key="commercial_view",
            )
            if commercial_view == "Financial Performance":
                render_commercial_intelligence(current_data)
            else:
                render_planning_workspace(current_data)
        else:
            st.info("Upload or activate a dataset in Data Workspace first.")


elif page == "Investment Intelligence":
    render_investment_intelligence(
        st.session_state.get("uploaded_df"),
        st.session_state.get("uploaded_name", "No active business dataset"),
    )

elif page == "Dashboard":
    dashboard_mode = st.radio(
        "Dashboard view",
        ["Executive Overview", "Detailed Analytics (Legacy)"],
        horizontal=True,
        key="dashboard_mode",
    )
    if dashboard_mode == "Executive Overview":
        if "uploaded_df" not in st.session_state:
            st.info("Select or upload a dataset in Data Workspace to view business analytics.")
        else:
            render_executive_dashboard(
                st.session_state["uploaded_df"].copy(),
                st.session_state.get("uploaded_name", "Active dataset"),
            )
    else:
        # Legacy tutorial dashboard assumes a specific workbook schema.
        # Redirect unsupported schemas rather than showing a broken/ambiguous result.
        if "uploaded_df" not in st.session_state:
            st.info("Choose or upload a dataset in Data Workspace before using Detailed Analytics.")
            st.stop()
        legacy_assessment = assess_legacy(st.session_state["uploaded_df"])
        if not legacy_assessment.compatible:
            tracked_render("Legacy compatible view", render_safe_details,
                           st.session_state["uploaded_df"], legacy_assessment)
            st.stop()
        st.header("Business KPI Dashboard")
        st.write("View important business metrics from your uploaded dataset.")

            # Load the prepared business dataset by default
        if "uploaded_df" not in st.session_state:
            try:
                st.session_state["uploaded_df"] = pd.read_excel(
                    "data/business/Python_BI_Complete_Business_Dataset.xlsx",
                    sheet_name="Business Data"
                )
            
                st.session_state["uploaded_name"] = "Default Business Dataset"

            except Exception as e:
                st.error(f"Unable to load the default dataset: {e}")

        # Check whether a dataset has been uploaded
        if "uploaded_df" not in st.session_state:
            st.info("Please upload a dataset first in the Data Explorer section.")

        else:
            df = st.session_state["uploaded_df"].copy()
        
            st.caption(
                f"Active dataset: {st.session_state.get('uploaded_name', 'Default Business Dataset')}"
            )


            if not df.empty and {"Sales", "Total Cost"}.issubset(df.columns):
                with st.expander("Financial Pulse — active dataset", expanded=False):
                    st.caption("A source-wide snapshot based on Sales and Total Cost. Not adjusted for returns, operating expenses or taxes.")
                    try:
                        _, financial_pulse = calculate_commercial_metrics(
                            df, revenue="Sales", cost="Total Cost"
                        )
                        pulse_a, pulse_b, pulse_c = st.columns(3)
                        pulse_a.metric("Revenue", f"{financial_pulse['net_revenue']:,.2f}")
                        pulse_b.metric("Mapped Costs", f"{financial_pulse['mapped_costs']:,.2f}")
                        pulse_c.metric("Profit After Mapped Costs", f"{financial_pulse['profit_after_mapped_costs']:,.2f}")
                    except (ValueError, TypeError, OverflowError) as error:
                        st.warning(f"Financial snapshot unavailable: {error}")

            if df.empty:
                st.warning("The uploaded dataset is empty.")

            else:
                # Task 1 and 2: Identify useful KPI columns
                numeric_columns = df.select_dtypes(
                    include="number"
                ).columns.tolist()

                # Identify suitable category columns
                preferred_category_columns = [
                    col for col in df.columns
                    if any(word in str(col).lower()
                           for word in ["product", "category", "item", "type", "segment"])
                ]

                text_columns = df.select_dtypes(
                    include=["object", "category", "str"]
                ).columns.tolist()

                # Prefer Product/Category columns instead of Date columns
                category_columns = preferred_category_columns or [
                    col for col in text_columns
                    if not any(word in str(col).lower()
                               for word in ["date", "time"])
                ]
            
            # STEP 7 - Sub-step 2: Add a Category Filter
            st.subheader("2. Category Filter")

            if "Product" in df.columns:
                product_options = sorted(
                    df["Product"].dropna().astype(str).unique()
                )

                selected_products = st.multiselect(
                    "Select product(s):",
                    options=product_options,
                    default=product_options
                )
            else:
                selected_products = []
                st.info("No Product column available for filtering.")

        
            # STEP 7 - Sub-step 3: Add a Date Filter
            st.subheader("3. Date Filter")

            if "Date" in df.columns:
                date_values = pd.to_datetime(
                    df["Date"], errors="coerce"
                ).dropna()

                if not date_values.empty:
                    min_date = date_values.min().date()
                    max_date = date_values.max().date()

                    selected_date_range = st.date_input(
                        "Select date range:",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date
                    )
                else:
                    selected_date_range = None
                    st.warning("No valid dates available.")
            else:
                selected_date_range = None
                st.info("No Date column available.")

        
            # STEP 7 - Sub-step 4: Add a Location Filter
            st.subheader("4. Location Filter")

            if "City" in df.columns:
                city_options = sorted(
                    df["City"].dropna().astype(str).unique()
                )

                selected_cities = st.multiselect(
                    "Select city/cities:",
                    options=city_options,
                    default=city_options
                )
            else:
                selected_cities = []
                st.info("No City column available.")

            if "Region" in df.columns:
                region_options = sorted(
                    df["Region"].dropna().astype(str).unique()
                )

                selected_regions = st.multiselect(
                    "Select region(s):",
                    options=region_options,
                    default=region_options
                )
            else:
                selected_regions = []
                st.info("No Region column available.")

        
            # STEP 7 - Sub-step 5: Add a Numeric Range Filter
            st.subheader("5. Numeric Range Filter")

            if "Sales" in df.columns:
                min_sales = float(df["Sales"].min())
                max_sales = float(df["Sales"].max())

                selected_sales_range = st.slider(
                    "Select Sales range:",
                    min_value=min_sales,
                    max_value=max_sales,
                    value=(min_sales, max_sales)
                )
            else:
                selected_sales_range = None

            if "Quantity" in df.columns:
                min_quantity = int(df["Quantity"].min())
                max_quantity = int(df["Quantity"].max())

                selected_quantity_range = st.slider(
                    "Select Quantity range:",
                    min_value=min_quantity,
                    max_value=max_quantity,
                    value=(min_quantity, max_quantity)
                )
            else:
                selected_quantity_range = None
            
            filtered_df = df.copy()

            # STEP 7 - Sub-step 6: Apply All Filters

            if selected_products and "Product" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Product"].astype(str).isin(selected_products)
                ]

            if selected_date_range is not None and "Date" in filtered_df.columns:
                filtered_dates = pd.to_datetime(
                    filtered_df["Date"], errors="coerce"
                )
                start_date, end_date = selected_date_range

                filtered_df = filtered_df[
                    filtered_dates.dt.date.between(start_date, end_date)
                ]

            if selected_cities and "City" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["City"].astype(str).isin(selected_cities)
                ]

            if selected_regions and "Region" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Region"].astype(str).isin(selected_regions)
                ]

            if selected_sales_range is not None and "Sales" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Sales"].between(
                        selected_sales_range[0],
                        selected_sales_range[1]
                    )
                ]

            if selected_quantity_range is not None and "Quantity" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Quantity"].between(
                        selected_quantity_range[0],
                        selected_quantity_range[1]
                    )
                ]

            # STEP 7 - Sub-step 9: Show Filter Feedback

            st.subheader("Filter Feedback")

            # Display the number of matching records
            matching_records = len(filtered_df)
            original_records = len(df)

            st.metric(
                "Matching Records",
                f"{matching_records:,}",
                f"Out of {original_records:,} original records"
            )

            # Display the filtered data preview
            st.subheader("Filtered Data Preview")

            st.dataframe(
                filtered_df.head(10),
                width="stretch"
            )
            # Task 3: Calculate total records
            total_records = len(filtered_df)

            st.subheader("1. Key Performance Indicators")

            # Find a suitable sales column
            sales_column = next(
                (col for col in numeric_columns
                if "sales" in str(col).lower()),
                numeric_columns[0] if numeric_columns else None
            )

            if sales_column is not None:
                # Task 4 and 5: Total and average
                total_value = filtered_df[sales_column].sum()
                average_value = filtered_df[sales_column].mean()

                # Task 7: Minimum and maximum
                minimum_value = filtered_df[sales_column].min()
                maximum_value = filtered_df[sales_column].max()
            else:
                total_value = None
                average_value = None
                minimum_value = None
                maximum_value = None

            # Task 6: Calculate category counts
            if category_columns:
                category_column = category_columns[0]
                category_count = filtered_df[category_column].nunique()
            else:
                category_column = None
                category_count = None

            # Task 8: Calculate an additional business metric
            quantity_column = next(
                (col for col in numeric_columns
                if "quantity" in str(col).lower()),
                None
            )

            if quantity_column:
                extra_metric = filtered_df[quantity_column].sum()
                extra_label = "Total Quantity"
            elif category_count is not None:
                extra_metric = category_count
                extra_label = "Unique Categories"
            else:
                extra_metric = None
                extra_label = None

            # Task 9: Display KPI cards
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            kpi1.metric("Total Records", f"{total_records:,}")

            if sales_column is not None:
                kpi2.metric(
                    f"Total {sales_column}",
                    f"{total_value:,.2f}"
                )
                kpi3.metric(
                    f"Average {sales_column}",
                    f"{average_value:,.2f}"
                )
            else:
                kpi2.metric("Total Value", "Not available")
                kpi3.metric("Average Value", "Not available")

            if extra_metric is not None:
                kpi4.metric(extra_label, f"{extra_metric:,.0f}")
            else:
                kpi4.metric("Extra Metric", "Not available")

            # Show minimum and maximum values
            if sales_column is not None:
                st.subheader(f"2. Minimum and Maximum {sales_column}")

                min_col, max_col = st.columns(2)
                min_col.metric("Minimum", f"{minimum_value:,.2f}")
                max_col.metric("Maximum", f"{maximum_value:,.2f}")

            # Show category frequencies
            if category_column is not None:
                st.subheader("3. Category Counts")

                category_summary = (
                    df[category_column]
                    .value_counts()
                    .reset_index()
                )

                category_summary.columns = [
                    category_column, "Count"
                ]

                st.dataframe(
                    category_summary,
                    width="stretch"
                )
        
            # STEP 6 - Interactive Charts

            st.subheader("2. Choose a Chart Question")

            chart_question = st.selectbox(
                "What would you like to analyse?",
                [
                    "Compare categories",
                    "Show changes over time",
                    "Examine proportions",
                    "Explore relationships between two numeric variables"
                ]
            )

            st.write("Selected analysis:", chart_question)

            # STEP 6 - Sub-step 3: Select Chart Fields

            st.subheader("3. Select Chart Fields")

            # Select X-axis column
            if chart_question == "Explore relationships between two numeric variables":
                if numeric_columns:
                    chart_x_column = st.selectbox(
                        "Select a numeric X-axis column:",
                        numeric_columns,
                        key="chart_x_numeric"
                    )
                else:
                    chart_x_column = None
                    st.warning("No numeric columns available for X-axis.")

            else:
                if category_columns:
                    chart_x_column = st.selectbox(
                        "Select a category or X-axis column:",
                        category_columns,
                        key="chart_x_column"
                    )
                else:
                    chart_x_column = None
                    st.warning("No category columns available.")

            # Select numeric column for Y-axis
            if numeric_columns:
                chart_y_column = st.selectbox(
                    "Select a numeric or Y-axis column:",
                    numeric_columns,
                    key="chart_y_column"
                )
            else:
                chart_y_column = None
                st.warning("No numeric columns available.")

            st.write("Selected X-axis:", chart_x_column)
            st.write("Selected Y-axis:", chart_y_column)
            # STEP 6 - Sub-step 4: Generate Interactive Charts

            st.subheader("4. Interactive Chart")

            import plotly.express as px

            if chart_x_column is not None and chart_y_column is not None:

                if chart_question == "Compare categories":

                    chart_data = filtered_df.groupby(
                        chart_x_column
                    )[chart_y_column].sum().reset_index()

                    fig = px.bar(
                        chart_data,
                        x=chart_x_column,
                        y=chart_y_column,
                        title="Sales Comparison by Category"
                    )

                    st.plotly_chart(fig, use_container_width=True)
                elif chart_question == "Show changes over time":

                    if "Date" in df.columns:

                        chart_data = filtered_df.copy()

                        chart_data["Date"] = pd.to_datetime(
                            chart_data["Date"],
                            errors="coerce"
                        )

                        chart_data = chart_data.dropna(subset=["Date"])

                        chart_data = chart_data.groupby(
                            "Date"
                        )[chart_y_column].sum().reset_index()

                        fig = px.line(
                            chart_data,
                            x="Date",
                            y=chart_y_column,
                            title="Changes Over Time",
                            markers=True
                        )

                        st.plotly_chart(fig, use_container_width=True)

                    else:
                        st.warning("No Date column available.")
            
                elif chart_question == "Examine proportions":
                    chart_data = filtered_df.groupby(
                        chart_x_column
                    )[chart_y_column].sum().reset_index()

                    fig = px.pie(
                        chart_data,
                        names=chart_x_column,
                        values=chart_y_column,
                        title="Proportion by Category"
                    )

                    st.plotly_chart(fig, use_container_width=True)
                elif chart_question == "Explore relationships between two numeric variables":
                    fig = px.scatter(
                        filtered_df,
                        x=chart_x_column,
                        y=chart_y_column,
                        title="Relationship Between Two Variables"
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # STEP 8 - Sub-step 1: Understand Calculated Fields

                st.header("Step 8: Calculated Measures, Grouping & Relationships")

                st.subheader("1. Understand Calculated Fields")

                st.write(
                    "Calculated fields help us create new information "
                    "from existing dataset columns."
                )

                st.markdown("**A. Row-Level Calculated Column**")

                st.write(
                    "A row-level calculation performs a calculation "
                    "separately for every record in the dataset."
                )

                st.code(
                    'df["Sales per Unit"] = df["Sales"] / df["Quantity"]',
                    language="python"
                )

                st.markdown("**B. Summary Measure**")

                st.write(
                    "A summary measure calculates information across "
                    "multiple records."
                )

                st.code(
                    'total_sales = df["Sales"].sum()\n'
                    'average_sales = df["Sales"].mean()',
                    language="python"
                )

                st.success(
                    "You can now distinguish calculated columns "
                    "from summary measures."
                )

            # STEP 8 - Sub-step 2: Choose Source Columns

            st.subheader("2. Choose Source Columns")

            numeric_columns = df.select_dtypes(
                include="number"
            ).columns.tolist()

            st.write("Available numeric columns:", numeric_columns)

            if len(numeric_columns) >= 2:

                sales_column = st.selectbox(
                    "Select Sales Column:",
                    numeric_columns
                )

                quantity_column = st.selectbox(
                    "Select Quantity Column:",
                    numeric_columns,
                    index=min(1, len(numeric_columns) - 1)
                )

                st.success(
                    "Source columns selected successfully."
                )

            else:
                st.warning(
                    "At least two numeric columns are required."
                )

            # STEP 8 - Sub-step 3: Create a Calculated Column

            st.subheader("3. Create a Calculated Column")

            if len(numeric_columns) >= 2:

                calculated_df = df.copy()

                calculated_df["Sales per Unit"] = (
                    calculated_df[sales_column] /
                    calculated_df[quantity_column].replace(0, pd.NA)
                )

                st.write("Calculated Sales per Unit:")

                st.dataframe(
                    calculated_df[
                        [sales_column, quantity_column, "Sales per Unit"]
                    ],
                    width="stretch"
                )

                st.success("Calculated column created successfully.")

            # STEP 8 - Sub-step 4: Create Summary Measures

            # STEP 8 - Sub-step 5: Create Reusable Summary Functions
            def calculate_summary(data, column):
                return {
                    "Total": data[column].sum(),
                    "Average": data[column].mean(),
                    "Minimum": data[column].min(),
                    "Maximum": data[column].max()
                }

            st.subheader("4. Create Summary Measures")

            sales_summary = calculate_summary(df, "Sales")
            cost_summary = calculate_summary(df, "Total Cost")
            profit_summary = calculate_summary(df, "Profit")
            margin_summary = calculate_summary(df, "Profit Margin (%)")

            total_sales = sales_summary["Total"]
            average_sales = sales_summary["Average"]
            total_cost = cost_summary["Total"]
            total_profit = profit_summary["Total"]
            average_profit_margin = margin_summary["Average"]
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Sales", f"{total_sales:,.2f}")

            with col2:
                st.metric("Total Cost", f"{total_cost:,.2f}")

            with col3:
                st.metric("Total Profit", f"{total_profit:,.2f}")

            col4, col5 = st.columns(2)

            with col4:
                st.metric("Average Sales", f"{average_sales:,.2f}")

            with col5:
                st.metric("Average Profit Margin", f"{average_profit_margin:.2f}%")

            # STEP 8 - Sub-step 6: Group by One Category

            st.subheader("6. Group by One Category")

            product_summary = df.groupby("Product", as_index=False).agg(
                Total_Sales=("Sales", "sum"),
                Total_Cost=("Total Cost", "sum"),
                Total_Profit=("Profit", "sum")
            )

            st.write("Product-wise Business Summary:")

            st.dataframe(
                product_summary,
                width="stretch"
            )

            # STEP 8 - Sub-step 7: Group by Multiple Fields

            st.subheader("7. Group by Multiple Fields")

            region_product_summary = df.groupby(
                ["Region", "Product"],
                as_index=False
            ).agg(
                Total_Sales=("Sales", "sum"),
                Total_Cost=("Total Cost", "sum"),
                Total_Profit=("Profit", "sum")
            )

            st.write("Region-wise and Product-wise Business Summary:")

            st.dataframe(
                region_product_summary,
                width="stretch"
            )

            # STEP 8 - Sub-step 8: Sort and Present Grouped Results

            st.subheader("8. Sort and Present Grouped Results")

            sorted_summary = region_product_summary.sort_values(
                by="Total_Sales",
                ascending=False
            )

            st.write("Grouped Business Results (Highest Sales First):")

            st.dataframe(
                sorted_summary,
                width="stretch"
            )
            # STEP 8 - Sub-step 9: Introduce Basic Data Relationships

            st.subheader("9. Introduce Basic Data Relationships")

            try:
                product_details = pd.read_excel(
                    "data/business/Python_BI_Complete_Business_Dataset.xlsx",
                    sheet_name="Product Details"
                )

                customer_details = pd.read_excel(
                    "data/business/Python_BI_Complete_Business_Dataset.xlsx",
                    sheet_name="Customer Details"
                )

                st.write("Product Details Preview:")
                st.dataframe(product_details.head(), width="stretch")

                st.write("Customer Details Preview:")
                st.dataframe(customer_details.head(), width="stretch")

                # Check relationship keys

                st.write("Checking Relationship Keys:")

                st.write(
                    "Duplicate Product IDs:",
                    product_details["ProductID"].duplicated().sum()
                )

                st.write(
                    "Missing Product IDs:",
                    product_details["ProductID"].isna().sum()
                )

                st.write(
                    "Duplicate Customer IDs:",
                    customer_details["CustomerID"].duplicated().sum()
                )

                st.write(
                    "Missing Customer IDs:",
                    customer_details["CustomerID"].isna().sum()
                )

                        # Merge Product Details with Main Dataset
                merged_df = df.merge(
                    product_details[["ProductID", "Category", "Standard Unit Cost"]],
                    on="ProductID",
                    how="left",
                    validate="many_to_one"
                )

                # Merge Customer Details with the Merged Dataset
                merged_df = merged_df.merge(
                    customer_details,
                    on="CustomerID",
                    how="left",
                    suffixes=("", "_customer"),
                    validate="many_to_one"
                )

                # Display Merged Dataset
                st.subheader("Merged Business Dataset")
                st.write("Main dataset joined with Product and Customer Details:")
                st.dataframe(merged_df.head(10), width="stretch")

                # STEP 8 - Sub-step 10: Validate Calculations and Joins

                st.subheader("10. Validate Calculations and Joins")

                # Compare row counts before and after merging
                original_rows = len(df)
                merged_rows = len(merged_df)

                # Compare total sales before and after merging
                original_sales = pd.to_numeric(
                    df["Sales"], errors="coerce"
                ).sum()

                merged_sales = pd.to_numeric(
                    merged_df["Sales"], errors="coerce"
                ).sum()

                # Check for unmatched Product IDs
                missing_product_matches = (
                    ~df["ProductID"].isin(product_details["ProductID"])
                ).sum()

                # Check for unmatched Customer IDs
                missing_customer_matches = (
                    ~df["CustomerID"].isin(customer_details["CustomerID"])
                ).sum()

                st.write("Validation Results:")

                st.metric("Original Rows", original_rows)
                st.metric("Rows After Merging", merged_rows)

                st.metric("Original Total Sales", f"{original_sales:,.2f}")
                st.metric("Merged Total Sales", f"{merged_sales:,.2f}")

                st.metric("Unmatched Product IDs", missing_product_matches)
                st.metric("Unmatched Customer IDs", missing_customer_matches)

                if original_rows == merged_rows and original_sales == merged_sales:
                    st.success("Validation successful: Row count and total sales are preserved.")
                else:
                    st.warning("Validation check failed: Please review the joins.")

            except Exception as e:
                st.error(f"Unable to load related tables: {e}")
