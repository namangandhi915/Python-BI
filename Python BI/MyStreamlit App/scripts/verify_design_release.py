"""Verify installed project files against the SHA-256 design-release manifest.

This checks copied-file integrity only; it does not audit code correctness or
certify that the app is safe for public deployment.
"""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
from pathlib import Path
import hashlib
import json

ROOT=PROJECT_ROOT
MANIFEST=ROOT/'manifests/DESIGN_RELEASE_MANIFEST.json'


def check(root:Path=ROOT)->tuple[bool,list[str]]:
    manifest_path=root/'manifests/DESIGN_RELEASE_MANIFEST.json'
    if not manifest_path.is_file():return False,['DESIGN_RELEASE_MANIFEST.json missing']
    try:
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    except (ValueError,OSError):return False,['Manifest cannot be parsed']
    if manifest.get('product')!='Python BI Studio' or manifest.get('release')!='Enterprise Design & Release Readiness 1':
        return False,['Unexpected manifest identity']
    files=manifest.get('files',{})
    if not isinstance(files,dict) or not files:return False,['Manifest has no files']
    errors=[]
    for relative,hash_expected in files.items():
        path=Path(relative)
        if path.is_absolute() or '..' in path.parts or str(path).startswith('\\'):
            errors.append('Unsafe file entry')
            continue
        target=root/path
        if not target.is_file():errors.append('Missing: '+relative);continue
        actual=hashlib.sha256(target.read_bytes()).hexdigest()
        if actual!=hash_expected:errors.append('Hash mismatch: '+relative)
    return not errors,errors


def main()->int:
    ok,errors=check()
    if ok:
        mapping=json.loads(MANIFEST.read_text())['files']
        print(f'PASS: {len(mapping)} design-release files match the supplied SHA-256 manifest.')
        print('This verifies file copies only; public deployment remains blocked.')
        return 0
    for error in errors:print('FAIL:',error)
    return 1

if __name__=='__main__':raise SystemExit(main())
