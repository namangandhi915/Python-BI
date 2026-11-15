"""Check all installed release files against the supplied SHA-256 manifest.

Run after replacing/copying files into the MyStreamlit App project root.
This is local integrity verification, not a software security certification.
"""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
import hashlib
import json
from pathlib import Path

ROOT=PROJECT_ROOT

def main()->int:
    manifest_path=ROOT/'manifests/FILE_MANIFEST.json'
    if not manifest_path.exists():
        print('FAIL: FILE_MANIFEST.json is missing from the project root.')
        return 1
    mapping=json.loads(manifest_path.read_text(encoding='utf-8'))
    if mapping.get('product')!='Python BI Studio Enterprise Assurance Release':
        print('FAIL: Unexpected release manifest.')
        return 1
    errors=[]
    files=mapping.get('files',{})
    if not files:
        print('FAIL: No release entries found in manifest.')
        return 1
    for filename, expected in files.items():
        if Path(filename).is_absolute() or '..' in Path(filename).parts or '\\' in filename:
            errors.append('Unsafe manifest filename')
            continue
        path=ROOT/filename
        if not path.is_file():
            errors.append(f'Missing: {filename}')
            continue
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=expected:
            errors.append(f'Mismatch: {filename}')
    if errors:
        for error in errors:print('FAIL:',error)
        return 1
    print(f'PASS: {len(files)} installed code/theme files match the release SHA-256 manifest.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
