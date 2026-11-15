"""Auditable ZIP containing ONLY aggregate executive-report outputs.

No network calls or raw source transaction rows. Chosen grouping labels may be sensitive.
The source report must already have passed report_engine reconciliation.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Mapping

import pandas as pd
from audit_exports import excel_safe_csv

MAX_PAYLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_REPORT_FILES = {
    "README.txt", "report.html", "financial_summary.csv",
    "category_performance.csv", "calendar_revenue.csv",
}


def build_report_archive(
    report: Mapping[str, object], *, dataset_name: str, filter_context: str,
    period: str, category: str | None, currency: str,
) -> bytes:
    """Package reconciled report tables with file digests for independent checking."""
    required = ("html", "summary", "categories", "periods", "matching_rows")
    if any(name not in report for name in required):
        raise ValueError("The executive report is incomplete; ZIP creation blocked.")
    html = report["html"]
    if not isinstance(html, bytes) or not html.startswith(b"<!DOCTYPE html>"):
        raise ValueError("Report HTML must be a complete UTF-8 HTML document.")
    summary, groups, periods = (report[k] for k in ("summary", "categories", "periods"))
    if not all(isinstance(x, pd.DataFrame) for x in (summary, groups, periods)):
        raise ValueError("Report tables must be Pandas dataframes.")
    rows = report["matching_rows"]
    if not isinstance(rows, int) or isinstance(rows, bool) or rows < 1:
        raise ValueError("Report matching-row count is invalid.")
    # This is intentionally an aggregate-only archive. The full row audit remains
    # a separate explicit download in Dashboard Section 03.
    files: dict[str, bytes] = {
        "report.html": html,
        "financial_summary.csv": excel_safe_csv(summary),
        "README.txt": (
            "PYTHON BI STUDIO — EXECUTIVE REPORT PACK\n\n"
            "Contents: print-ready report.html, financial_summary.csv, optional\n"
            "category_performance.csv and calendar_revenue.csv, and manifest.json.\n"
            "Raw transaction rows are not included. Category labels may identify people\n"
            "if you selected a customer/name/ID field. Review before sharing.\n"
            "Financial values use the selected dashboard filters and mappings.\n"
            "Profit after mapped costs is NOT necessarily accounting net profit.\n"
            "Financial reports are not investment advice.\n"
            "File SHA-256 values are listed in manifest.json. To verify them run:\n"
            "  python verify_report_pack.py python_bi_executive_report_pack.zip\n"
            "This manifest verifies ZIP content integrity, not authorship/signature.\n"
        ).encode("utf-8"),
    }
    if not groups.empty:
        files["category_performance.csv"] = excel_safe_csv(groups)
    if not periods.empty:
        files["calendar_revenue.csv"] = excel_safe_csv(periods)
    total_size = sum(map(len, files.values()))
    if total_size > MAX_PAYLOAD_BYTES:
        raise ValueError("Aggregate report exceeds the 25 MiB ZIP input limit; use individual CSV downloads.")
    digests = {
        filename: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        for filename, data in sorted(files.items())
    }
    manifest = {
        "schema_version": 1,
        "product": "Python BI Studio",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_label": str(dataset_name),
        "filters": str(filter_context),
        "calendar_period": str(period),
        "category_field": None if category is None else str(category),
        "currency_label": str(currency),
        "filtered_row_count": rows,
        "includes_transaction_level_data": False,
        "includes_category_labels": not groups.empty,
        "reconciled_report": True,
        "files": digests,
    }
    files["manifest.json"] = json.dumps(
        manifest, indent=2, ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for filename in sorted(files):
            zf.writestr(filename, files[filename])
    return buffer.getvalue()


def verify_report_archive(data: bytes) -> dict:
    """Verify complete archive integrity without extracting files to disk."""
    if not isinstance(data, bytes) or len(data) > MAX_PAYLOAD_BYTES * 2:
        raise ValueError("Invalid or oversized report archive.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data), "r")
        with zf:
            info = zf.infolist()
            names = [item.filename for item in info]
            if (len(names) != len(set(names)) or "manifest.json" not in names
                    or len(names) > len(ALLOWED_REPORT_FILES) + 1
                    or any(n not in ALLOWED_REPORT_FILES | {"manifest.json"} for n in names)):
                raise ValueError("The report pack has unexpected or duplicate files.")
            if sum(f.file_size for f in info) > MAX_PAYLOAD_BYTES:
                raise ValueError("Uncompressed report pack is too large.")
            meta = json.loads(zf.read("manifest.json"))
            if (meta.get("schema_version") != 1
                    or meta.get("includes_transaction_level_data") is not False
                    or meta.get("reconciled_report") is not True):
                raise ValueError("Report manifest schema is invalid.")
            if set(meta["files"]) != set(names) - {"manifest.json"}:
                raise ValueError("Manifest file list does not match the ZIP.")
            for filename, expected in meta["files"].items():
                contents = zf.read(filename)
                if (len(contents) != expected["bytes"]
                        or hashlib.sha256(contents).hexdigest() != expected["sha256"]):
                    raise ValueError(f"Report content failed integrity verification: {filename}.")
            return meta
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Report archive is invalid: {exc}") from exc
