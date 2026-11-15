"""Append safe ignore patterns to .gitignore without deleting any existing rules.

Warning: .gitignore changes do NOT remove files previously committed to Git.
This command changes only .gitignore, not uploaded datasets or histories.
"""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
from pathlib import Path
from deployment_audit import SENSITIVE_EXCLUSIONS


def add_ignores(root: Path) -> tuple[bool, tuple[str, ...]]:
    target = Path(root) / '.gitignore'
    original = target.read_text(encoding='utf-8') if target.exists() else ''
    existing = {line.strip() for line in original.splitlines()}
    missing = tuple(x for x in SENSITIVE_EXCLUSIONS if x not in existing)
    if missing:
        suffix = '' if not original or original.endswith('\n') else '\n'
        target.write_text(original + suffix + '\n# Python BI Studio — local data and release evidence\n' + '\n'.join(missing) + '\n', encoding='utf-8')
    return bool(missing), missing


def main() -> None:
    changed, added = add_ignores(PROJECT_ROOT)
    if changed:
        print('Appended', len(added), 'privacy patterns to .gitignore without deleting existing entries.')
    else:
        print('Privacy ignore patterns are already present. Nothing changed.')
    print('IMPORTANT: Review git ls-files separately; .gitignore does not untrack committed files.')

if __name__ == '__main__':
    main()
