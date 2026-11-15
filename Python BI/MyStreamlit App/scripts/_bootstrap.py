"""Shared paths for the project command-line tools."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = PROJECT_ROOT / "modules"

for path in (PROJECT_ROOT, MODULES_DIR):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
