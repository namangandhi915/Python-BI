"""Local dataset persistence, independent of Streamlit UI."""
from __future__ import annotations
import hashlib
import json
from uuid import uuid4
from local_file_guard import validate_upload, safe_stored_path

def save_active_dataset(uploaded_file, storage_dir):
    """Save uploads without duplicating identical files."""

    active_file = storage_dir / "active_dataset.json"
    file_info = validate_upload(uploaded_file)
    extension = file_info["extension"]

    storage_dir.mkdir(parents=True, exist_ok=True)

    file_bytes = uploaded_file.getvalue()
    file_hash = file_info["sha256"]

    stored_name = None

    # Search for an identical saved file.
    for existing_file in storage_dir.iterdir():
        if (
            existing_file.is_file()
            and not existing_file.is_symlink()
            and existing_file.suffix.lower() == extension
            and existing_file.stat().st_size == len(file_bytes)
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
        stored_path = safe_stored_path(storage_dir, stored_name)
        stored_path.write_bytes(file_bytes)

    metadata = {
        "name": uploaded_file.name,
        "stored_name": stored_name,
        "hash": file_hash
    }

    temporary_file = storage_dir / "active_dataset.tmp"

    temporary_file.write_text(
        json.dumps(metadata),
        encoding="utf-8"
    )

    temporary_file.replace(active_file)
