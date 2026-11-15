"""Data-minimising release evidence (no raw records, secrets or source paths)."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from html import escape
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from deployment_audit import check_deployment, release_gate
from pathlib import Path


def build_report(root: Path) -> dict:
    checks = check_deployment(root)
    counts = {label: sum(c["status"] == label for c in checks) for label in ("PASS", "REVIEW", "MANUAL", "BLOCKED")}
    return {
        "product": "Python BI Studio",
        "release": "Enterprise Design and Production Readiness Candidate 1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Offline local preflight; NOT an external security certification or public deployment",
        "gate": release_gate(checks),
        "counts": counts,
        "checks": checks,
    }


def html_report(report: dict) -> str:
    trs = "".join(
        "<tr><td>" + escape(x["id"]) + "</td><td>" + escape(x["status"]) + "</td><td>" + escape(x["area"]) + "</td><td>" + escape(x["finding"]) + "</td></tr>"
        for x in report["checks"]
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Python BI Studio - Release Readiness</title>'
        '<style>body{font:16px/1.6 Segoe UI,Arial,sans-serif;margin:40px auto;max-width:1000px;color:#142B4A}table{border-collapse:collapse;width:100%}td,th{border:1px solid #DCE5F0;padding:10px;text-align:left}th{background:#EDF2F8}h1{font-size:30px} .gate{padding:12px;background:#F5F7FA}</style>'
        f'<h1>{escape(report["product"])} — Release Readiness</h1><p>{escape(report["scope"])}</p>'
        f'<p class="gate">Release gate: <strong>{escape(report["gate"])}</strong></p>'
        '<table><thead><tr><th>ID</th><th>Status</th><th>Area</th><th>Finding</th></tr></thead><tbody>'
        + trs + '</tbody></table><p>This is a static audit snapshot. No user datasets are included.</p></html>'
    )


def evidence_zip(report: dict) -> bytes:
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as z:
        z.writestr("release_readiness.json", json.dumps(report, indent=2, ensure_ascii=False))
        z.writestr("release_readiness.html", html_report(report))
        z.writestr("README.txt", "Offline preflight only. Public deployment is BLOCKED pending user isolation, authentication and durable storage. No source records or credentials included.\n")
    return out.getvalue()
