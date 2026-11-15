"""Local-only file safety helpers. No authentication or cloud operations.

Guards reduce accidental / malformed inputs; they are NOT malware scanning,
secure multi-tenant storage, or certification for public deployment.
"""
from __future__ import annotations
from pathlib import Path
from io import BytesIO
import hashlib
import re
import zipfile

MAX_UPLOAD_MIB = 96
MAX_ARCHIVE_MIB = 512
MAX_ARCHIVE_ENTRIES = 20_000
_STORED = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\.(csv|xlsx)$", re.I)


def safe_stored_path(folder: Path, filename: str, *, must_exist: bool = False) -> Path:
    """Prevent metadata traversal, unwanted extensions and symlink-file reads."""
    if not isinstance(filename, str) or not _STORED.fullmatch(filename) or '..' in filename:
        raise ValueError("Invalid stored dataset filename.")
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError("Dataset Library folder cannot be a symbolic link.")
    base = folder.resolve()
    target = base / filename
    if target.is_symlink() or target.resolve().parent != base:
        raise ValueError("Dataset path is outside its library.")
    if must_exist and not target.is_file():
        raise FileNotFoundError("Saved dataset is missing.")
    return target


def validate_upload(upload, max_mib: int = MAX_UPLOAD_MIB) -> dict:
    """Check extension, byte limit and XLSX structure before calling Pandas."""
    if not isinstance(max_mib, int) or max_mib <= 0:
        raise ValueError("Maximum upload size must be positive.")
    name = str(getattr(upload, 'name', ''))
    if not name or Path(name).name != name or '\\' in name or '/' in name:
        raise ValueError("Upload name is invalid.")
    suffix = Path(name).suffix.lower()
    if suffix not in ('.csv', '.xlsx'):
        raise ValueError("Only CSV and XLSX datasets are supported.")
    maximum = max_mib * 1024 * 1024
    indicated = getattr(upload, 'size', None)
    if indicated is not None and indicated > maximum:
        raise ValueError(f"File exceeds the {max_mib} MiB local processing limit.")
    raw = upload.getvalue()
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("Dataset is empty or cannot be read.")
    if len(raw) > maximum:
        raise ValueError(f"File exceeds the {max_mib} MiB local processing limit.")
    if suffix == '.csv':
        if raw.startswith(b'PK\x03\x04') or b'\x00' in raw[:65536]:
            raise ValueError("CSV appears to be an archive or binary file.")
    else:
        if not zipfile.is_zipfile(BytesIO(raw)):
            raise ValueError("XLSX upload is not a valid Excel archive.")
        total = 0
        members = set()
        with zipfile.ZipFile(BytesIO(raw)) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise ValueError("Workbook contains too many archive entries.")
            for item in infos:
                member = item.filename.replace('\\', '/')
                if member.startswith('/') or '..' in member.split('/'):
                    raise ValueError("Unsafe workbook archive entry.")
                if item.flag_bits & 1:
                    raise ValueError("Encrypted workbook archives are unsupported.")
                total += item.file_size
                if total > MAX_ARCHIVE_MIB * 1024 * 1024:
                    raise ValueError("Workbook expands beyond the local processing limit.")
                members.add(member)
        if '[Content_Types].xml' not in members or 'xl/workbook.xml' not in members:
            raise ValueError("Workbook is missing required Excel components.")
    return {"name": name, "extension": suffix, "size_bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}
