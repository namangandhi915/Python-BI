"""Opt-in, exact installed-version dependency snapshot for VS Code.

Never overwrites requirements.txt automatically. Pinning is local-machine evidence,
not a guarantee of Windows-to-cloud compatibility.
"""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
import argparse
import importlib.metadata
from pathlib import Path
from deployment_audit import DEPENDENCIES


def dependency_lines() -> list[str]:
    result = []
    for name in DEPENDENCIES:
        result.append(f"{name}=={importlib.metadata.version(name)}")
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="requirements.release-candidate.txt")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args(argv)
    target = Path(args.output)
    if target.exists() and not args.overwrite:
        print("No changes: candidate file already exists. Use --overwrite explicitly to replace it.")
        return 2
    try:
        lines = dependency_lines()
    except importlib.metadata.PackageNotFoundError as e:
        print("A direct dependency is missing:", e)
        return 1
    target.write_text("# Local Python BI Studio dependency snapshot. Review before cloud use.\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print("Saved candidate requirements:", target.name)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
