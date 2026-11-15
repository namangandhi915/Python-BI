"""Read-only review of the locally stored active dataset; no data leaves the PC."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from local_file_guard import safe_stored_path


def audit_dataset_library(project_root: Path) -> dict:
    root = Path(project_root)
    folder = root / 'stored_datasets'
    active = folder / 'active_dataset.json'
    result = {"scope": "local single-user only", "dataset_library_present": folder.is_dir(),
              "active_metadata_present": active.is_file(), "saved_file_count": 0,
              "active_integrity": "NOT_CHECKED", "messages": []}
    if folder.is_symlink():
        result['active_integrity'] = 'UNSAFE_LIBRARY_PATH'
        return result
    if not folder.is_dir():
        result['messages'].append('Dataset Library not created yet.')
        return result
    for path in folder.iterdir():
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in ('.csv', '.xlsx'):
            try:
                safe_stored_path(folder, path.name)
                result['saved_file_count'] += 1
            except ValueError:
                pass
    if not active.exists():
        result['messages'].append('No active dataset metadata is present.')
        return result
    if active.is_symlink():
        result['active_integrity'] = 'UNSAFE_ACTIVE_METADATA'
        return result
    try:
        metadata = json.loads(active.read_text(encoding='utf-8'))
        target = safe_stored_path(folder, metadata['stored_name'], must_exist=True)
        expected = metadata.get('hash')
        if expected:
            result['active_integrity'] = ('PASS' if hashlib.sha256(target.read_bytes()).hexdigest() == expected
                                          else 'HASH_MISMATCH')
        else:
            result['active_integrity'] = 'LEGACY_NO_CHECKSUM'
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        result['active_integrity'] = 'REVIEW_REQUIRED'
    return result
