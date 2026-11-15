from _bootstrap import PROJECT_ROOT
"""Verify installed final-roadmap release files against its SHA-256 manifest.

Runs offline. Does not read datasets, credentials, or any other private files.
"""
from pathlib import Path
from hashlib import sha256
import json

ROOT=PROJECT_ROOT
MANIFEST=ROOT/'manifests/FINAL_ACCEPTANCE_MANIFEST.json'


def verify():
    data=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if data.get('release')!='Python BI Studio Final Roadmap Acceptance':
        raise AssertionError('Wrong release manifest.')
    files=data['files']
    if len(files)<10:
        raise AssertionError('Incomplete manifest.')
    for rel,expected in files.items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise AssertionError('Unsafe manifest path: '+rel)
        target=ROOT/rel
        if not target.is_file():raise AssertionError('Missing file: '+rel)
        digest=sha256(target.read_bytes()).hexdigest()
        if digest!=expected:raise AssertionError('Modified or incomplete file: '+rel)
    return len(files)

if __name__=='__main__':
    count=verify()
    print(f'PASS: {count} final-acceptance installation files match SHA-256 manifest.')
    print('Saved datasets and private project data were NOT scanned.')
