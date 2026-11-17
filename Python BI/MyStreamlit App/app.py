
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

import json
import hashlib
from pathlib import Path
import sys

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
from dataset_library import save_active_dataset as save_dataset_to_library
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
    """Save and activate an uploaded local dataset."""
    return save_dataset_to_library(uploaded_file, STORAGE_DIR)


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
        st.session_state["active_data_token"] = metadata.get("hash", stored_name)

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
library_upload = st.sidebar.file_uploader("Add a dataset to the library", type=["csv", "xlsx"], key="library_upload")
if library_upload is not None and st.sidebar.button("Save and activate dataset"):
    try:
        library_info = validate_upload(library_upload)
        library_frame = pd.read_csv(library_upload) if library_upload.name.lower().endswith(".csv") else pd.read_excel(library_upload)
        save_active_dataset(library_upload)
        st.session_state["uploaded_df"] = library_frame
        st.session_state["uploaded_name"] = library_upload.name
        st.session_state["active_data_token"] = library_info["sha256"]
        st.session_state.pop("explorer_datasets", None)
        st.session_state.pop("explorer_combined", None)
        st.session_state.pop("prep_upload_hash", None)
        st.session_state.pop("explorer_selected_files", None)
        st.session_state.pop("explorer_selection", None)
        st.session_state["uploader_version"] = st.session_state.get("uploader_version", 0) + 1
        metadata = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
        save_dataset_label(metadata["stored_name"], library_upload.name)
        st.rerun()
    except Exception as error:
        st.sidebar.error(f"Unable to save dataset: {error}")

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

            st.session_state.pop("explorer_datasets", None)
            st.session_state.pop("explorer_combined", None)
            st.session_state.pop("prep_upload_hash", None)
            st.session_state.pop("explorer_selected_files", None)
            st.session_state.pop("explorer_selection", None)
            # Update the shared dataset
            st.session_state["active_data_token"] = metadata["hash"]
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
    st.caption("Local use only: public deployment requires authentication and isolated dataset storage.")

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

   
        uploaded_files = st.file_uploader(
            "Add CSV or Excel files", type=["csv", "xlsx"], accept_multiple_files=True,
            key=f"explorer_uploader_{st.session_state.get('uploader_version', 0)}"
        )
        st.caption("New files are saved in the local Dataset Library. Select one or more files to analyse.")
        datasets = st.session_state.setdefault("explorer_datasets", {})
        new_ids = []
        for uploaded_file in uploaded_files:
            try:
                info = validate_upload(uploaded_file)
                identity = f"{info['sha256']}:{uploaded_file.name}"
                if identity not in datasets:
                    frame = pd.read_csv(uploaded_file) if uploaded_file.name.lower().endswith(".csv") else pd.read_excel(uploaded_file)
                    save_active_dataset(uploaded_file)
                    metadata = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
                    save_dataset_label(metadata["stored_name"], uploaded_file.name)
                    datasets[identity] = (uploaded_file.name, frame)
                    new_ids.append(identity)
            except Exception as error:
                st.error(f"Unable to load {uploaded_file.name}: {error}")
        if datasets:
            selection = st.session_state.get("explorer_selection", list(datasets))
            selection = [identity for identity in selection if identity in datasets]
            selection = list(dict.fromkeys(selection + new_ids))
            st.session_state["explorer_selection"] = selection
            st.session_state["explorer_selected_files"] = selection
            def remember_explorer_selection():
                st.session_state["explorer_selection"] = list(st.session_state["explorer_selected_files"])
            selected_files = st.multiselect(
                "Files to analyse together", list(datasets),
                format_func=lambda identity: f"{datasets[identity][0]} ({identity[:8]})",
                key="explorer_selected_files", on_change=remember_explorer_selection,
            )
            if selected_files:
                frames = [datasets[identity][1] for identity in selected_files]
                selection_key = tuple(selected_files)
                if len(frames) == 1:
                    df = frames[0]
                else:
                    cached = st.session_state.get("explorer_combined")
                    if cached is None or cached[0] != selection_key:
                        cached = (selection_key, pd.concat(frames, ignore_index=True, sort=False))
                        st.session_state["explorer_combined"] = cached
                    df = cached[1]
                if len(frames) > 1:
                    st.caption("Files are stacked by matching column names. Columns absent from a file have missing values; rows are not joined.")
                st.session_state["uploaded_df"] = df
                st.session_state["active_data_token"] = "explore:" + "|".join(selection_key)
                st.session_state["uploaded_name"] = ", ".join(datasets[identity][0] for identity in selected_files)
                render_explorer_workspace(df)
            else:
                st.info("Select at least one file to analyse.")
        elif "uploaded_df" in st.session_state:
            render_explorer_workspace(st.session_state["uploaded_df"])
        else:
            st.info("Upload a CSV or XLSX file to begin.")


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
                    info = validate_upload(uploaded_file)
                    if (st.session_state.get("prep_upload_hash") != info["sha256"]
                            or st.session_state.get("active_data_token") != info["sha256"]):
                        df = pd.read_csv(uploaded_file) if uploaded_file.name.lower().endswith(".csv") else pd.read_excel(uploaded_file)
                        st.session_state["uploaded_df"] = df
                        st.session_state["uploaded_name"] = uploaded_file.name
                        st.session_state["prep_upload_hash"] = info["sha256"]
                        st.session_state["active_data_token"] = info["sha256"]
                        save_active_dataset(uploaded_file)
                    else:
                        df = st.session_state["uploaded_df"]
                else:
                    df = st.session_state["uploaded_df"]


                # Create a display-safe copy of the uploaded data
                df_display = df.head(100).copy()

                # Convert mixed object columns to consistent text for display
            
                for col in [c for c in df_display.columns if pd.api.types.is_object_dtype(df_display[c].dtype)]:
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

                render_assurance_home(df)

                with st.expander('Missing-value records', expanded=False):
                    st.dataframe(df_display, width="stretch")
                    if st.checkbox("Find missing-value records", key="quality_find_missing"):
                        missing_scope = st.selectbox("Find records with missing values", ["Any column"] + df.columns.tolist(), key="quality_missing_scope")
                        affected = missing_records(df, None if missing_scope == "Any column" else missing_scope)
                        st.caption(f"{len(affected):,} affected rows found; showing the first 100.")
                        st.dataframe(affected.head(100), width="stretch")
                        if st.checkbox("Prepare affected-records export", key="quality_prepare_missing_export"):
                            st.download_button("Export affected records", affected.to_csv(index=False).encode("utf-8"), file_name="missing_records.csv", mime="text/csv", key="quality_missing_export")

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

                with st.expander('Text and numeric validation tools', expanded=False):
                    text_columns = clean_df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
                    st.caption("Leading and trailing whitespace is automatically removed from text values in the prepared copy.")
                    for column in text_columns:
                        clean_df[column] = clean_df[column].map(lambda value: value.strip() if isinstance(value, str) else value)

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

                        finite_values = np.isfinite(converted_values.to_numpy(dtype=float, na_value=np.nan))
                        invalid_mask = original_values.notna() & ~finite_values

                        invalid_count = int(invalid_mask.sum())

                        st.metric(
                            "Invalid Numeric Values",
                            invalid_count
                        )

                        show_all_invalid = st.checkbox("Show all invalid entries", key="prep_all_invalid")
                        invalid_limit = int(st.number_input("Invalid entries to show", min_value=1, max_value=1_000_000, value=100, step=100, key="prep_invalid_limit"))
                        if invalid_count:
                            invalid_rows = clean_df.loc[invalid_mask]
                            st.dataframe(invalid_rows if show_all_invalid else invalid_rows.head(invalid_limit), width="stretch")

                with st.expander('Results and export', expanded=True):
                    st.markdown("**Preparation results**")
                    before, after = st.columns(2)
                    before.metric("Original rows", f"{len(df):,}")
                    after.metric("Prepared rows", f"{len(clean_df):,}")
                    if st.checkbox("Calculate exact before and after quality counts", key="prep_exact_counts"):
                        source_quality = quality_overview(df)
                        prepared_quality = quality_overview(clean_df)
                        before.metric("Original missing cells", f"{source_quality['missing_cells']:,}")
                        before.metric("Original duplicates", f"{source_quality['duplicate_rows']:,}")
                        after.metric("Prepared missing cells", f"{prepared_quality['missing_cells']:,}")
                        after.metric("Prepared duplicates", f"{prepared_quality['duplicate_rows']:,}")

                    st.dataframe(clean_df.head(100), width="stretch")

                    st.markdown("**Export prepared dataset**")
                    if st.checkbox("Prepare cleaned CSV download", key="prepare_cleaned_csv"):
                        csv_data = clean_df.to_csv(index=False).encode("utf-8")
                        st.download_button(label="Download cleaned CSV", data=csv_data, file_name="cleaned_data.csv", mime="text/csv")

            except Exception as e:
                st.error(
                    "Could not process this file. Please check that it is "
                    "a valid CSV or XLSX file."
                )
                st.caption(f"Technical details: {e}")



    else:
        commercial_view = st.radio(
            "Commercial tools",
            ["Financial Performance", "Business Planning"],
            horizontal=True,
            key="commercial_view",
        )
        if commercial_view == "Financial Performance":
            if "uploaded_df" in st.session_state:
                current_data = st.session_state["uploaded_df"]
                render_commercial_intelligence(current_data)
            else:
                st.info("Upload or activate a dataset to calculate financial performance.")
        else:
            current_data = st.session_state.get("uploaded_df", pd.DataFrame())
            render_planning_workspace(current_data)


elif page == "Investment Intelligence":
    render_investment_intelligence(
        st.session_state.get("uploaded_df"),
        st.session_state.get("uploaded_name", "No active business dataset"),
    )

elif page == "Dashboard":
    if "uploaded_df" not in st.session_state:
        st.info("Select or upload a dataset in Data Workspace to view business analytics.")
    else:
        render_executive_dashboard(st.session_state["uploaded_df"], st.session_state.get("uploaded_name", "Active dataset"))
