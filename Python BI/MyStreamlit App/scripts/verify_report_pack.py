"""Optional verifier for local executive-report ZIP downloads."""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
import argparse
from pathlib import Path
from report_bundle import verify_report_archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Check aggregate report ZIP SHA-256 integrity.")
    parser.add_argument("report_zip", type=Path, help="Path to downloaded report pack ZIP")
    args = parser.parse_args()
    try:
        meta = verify_report_archive(args.report_zip.read_bytes())
    except (ValueError, OSError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print(f"PASS: {len(meta['files'])} report files match the manifest")
    print(f"Dataset: {meta['dataset_label']}; filtered rows: {meta['filtered_row_count']}")
    print("Note: Checksums verify integrity, not report authorship or accounting correctness.")

if __name__ == "__main__":
    main()
