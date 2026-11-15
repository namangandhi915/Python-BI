"""Conservative read-only deployment preflight for a *single-user local* BI app.

An automated audit must never claim the current shared filesystem Dataset
Library is safe for anonymous public or multi-tenant operation.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import importlib.metadata
import tomllib

DEPENDENCIES = ("streamlit", "pandas", "numpy", "plotly", "openpyxl")
SENSITIVE_EXCLUSIONS = ("stored_datasets/", "Data/", ".venv/", "__pycache__/", ".streamlit/secrets.toml", ".env", "assurance_results/", "release_results/", "benchmark_artifacts/")

@dataclass(frozen=True)
class Check:
    id: str
    status: str
    area: str
    finding: str

    def as_dict(self) -> dict:
        return {"id": self.id, "status": self.status, "area": self.area, "finding": self.finding}


def check_deployment(root: Path) -> list[dict]:
    """Never includes file contents, credentials or absolute source paths in results."""
    root = Path(root)
    findings = [
        Check("AUTH", "BLOCKED", "Access control", "No verified authentication and user-authorisation boundary for business files."),
        Check("USER-ISOLATION", "BLOCKED", "Data isolation", "stored_datasets and active_dataset.json are shared filesystem state; per-user storage is not implemented."),
        Check("PERSISTENCE", "BLOCKED", "Durability", "Local server files are not a managed, durable multi-user dataset store."),
        Check("EXTERNAL-SECURITY", "MANUAL", "Security", "Threat modelling, penetration testing, upload quotas and operating controls require an independent review."),
        Check("BROWSER-TEST", "MANUAL", "Acceptance", "Browser-level multi-schema, 500k workflow and regression tests require documented human acceptance."),
        Check("DEPLOYMENT", "MANUAL", "Release", "Cloud environment, routing, access and recovery have not been commissioned or verified."),
    ]
    for name in DEPENDENCIES:
        try:
            version = importlib.metadata.version(name)
            findings.append(Check(f"DEP:{name}", "PASS", "Dependencies", f"{name} installed ({version})."))
        except importlib.metadata.PackageNotFoundError:
            findings.append(Check(f"DEP:{name}", "REVIEW", "Dependencies", f"{name} not installed in the Python environment running this audit."))

    config = root / ".streamlit" / "config.toml"
    try:
        theme = tomllib.loads(config.read_text(encoding="utf-8")).get("theme", {})
        if theme.get("base") == "light":
            findings.append(Check("LIGHT-THEME", "PASS", "Appearance", "Project config retains the requested light base theme."))
        else:
            findings.append(Check("LIGHT-THEME", "REVIEW", "Appearance", "Check the light-theme base setting."))
    except (OSError, ValueError):
        findings.append(Check("LIGHT-THEME", "REVIEW", "Appearance", "Configuration file is missing or unreadable."))

    ignore_path = root / ".gitignore"
    if not ignore_path.exists():
        findings.append(Check("PRIVATE-GIT", "REVIEW", "Source control", "No .gitignore found. Keep private datasets and secrets out of Git."))
    else:
        contents = ignore_path.read_text(encoding="utf-8", errors="replace").splitlines()
        rules = {line.strip() for line in contents if line.strip() and not line.lstrip().startswith("#")}
        missing = [rule for rule in SENSITIVE_EXCLUSIONS if rule not in rules]
        if not missing:
            findings.append(Check("PRIVATE-GIT", "PASS", "Source control", "Recommended privacy patterns appear in .gitignore (tracking status not established)."))
        else:
            findings.append(Check("PRIVATE-GIT", "REVIEW", "Source control", "Missing recommended ignore patterns: " + ", ".join(missing)))
    findings.append(Check("REPOSITORY-REVIEW", "MANUAL", "Source control", "Check git tracked files, history, workbook contents and any remote repository before publishing."))
    return [f.as_dict() for f in findings]


def release_gate(checks: list[dict]) -> str:
    return "BLOCKED_FOR_PUBLIC_DEPLOYMENT" if any(x["status"] == "BLOCKED" for x in checks) else "MANUAL_APPROVAL_REQUIRED"


def public_blockers(checks: list[dict]) -> int:
    return sum(x["status"] == "BLOCKED" for x in checks)
