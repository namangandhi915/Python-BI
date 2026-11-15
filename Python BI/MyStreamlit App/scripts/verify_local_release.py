"""Verify this package's own file digests after installation, without old-manifest confusion."""
from __future__ import annotations
from _bootstrap import PROJECT_ROOT
import hashlib,json
from pathlib import Path
ROOT=PROJECT_ROOT


def verify(root=ROOT):
    root=Path(root)
    manifest=root/'manifests/LOCAL_REVIEW_MANIFEST.json'
    if not manifest.is_file():return False,['LOCAL_REVIEW_MANIFEST.json is missing']
    try:info=json.loads(manifest.read_text(encoding='utf-8'))
    except (ValueError,OSError):return False,['Invalid local release manifest']
    if info.get('release')!='Local Roadmap Validation & Offline Demonstration — No Review Website Panel':
        return False,['Unexpected release identity']
    files=info.get('files',{})
    if not files or not isinstance(files,dict):return False,['Manifest contains no files']
    errors=[]
    for name,digest in files.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name:
            errors.append('Unsafe manifest entry');continue
        target=root/p
        if not target.is_file(): errors.append('Missing: '+name)
        elif hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
            errors.append('Changed: '+name)
    return not errors,errors

if __name__=='__main__':
    good,errors=verify()
    if good:
        print('PASS: Corrected local-only roadmap release files match SHA-256 manifest.')
    else:
        for error in errors:print('FAIL:',error)
    raise SystemExit(0 if good else 1)
