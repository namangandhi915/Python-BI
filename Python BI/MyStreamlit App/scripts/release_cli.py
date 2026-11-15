"""Offline local preflight and release-evidence generator.

Runs no server, deploys nothing and intentionally refuses to claim public readiness.
"""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
import argparse
import json
from pathlib import Path
from release_evidence import build_report, html_report, evidence_zip


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Python BI Studio local release preflight")
    parser.add_argument("--output", default="outputs/release_results", help="Local evidence output directory")
    args = parser.parse_args(argv)
    root = PROJECT_ROOT
    out = Path(args.output)
    if not out.is_absolute(): out = root / out
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(root)
    (out / "release_readiness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "release_readiness.html").write_text(html_report(report), encoding="utf-8")
    (out / "release_readiness_pack.zip").write_bytes(evidence_zip(report))
    print("Python BI Studio — local release preflight")
    print("Release gate:", report["gate"])
    for name, count in report["counts"].items(): print(f"{name}: {count}")
    print("Created outputs/release_results/ release-readiness JSON, HTML and ZIP evidence.")
    print("NOTICE: Do not publicly deploy shared Dataset Library storage without user isolation.")
    return 0   # Zero means the preflight ran correctly; it does NOT mean approval.

if __name__ == "__main__":
    raise SystemExit(main())
