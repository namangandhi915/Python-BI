from pathlib import Path
from tempfile import TemporaryDirectory
import json,hashlib
from local_recovery_audit import audit_dataset_library

def main():
    with TemporaryDirectory() as temp:
        root=Path(temp); d=root/'stored_datasets'; d.mkdir()
        a=audit_dataset_library(root)
        assert a['saved_file_count']==0 and a['active_integrity']=='NOT_CHECKED'
        name='abcd1234abcd1234abcd1234abcd1234.csv'; data=b'A,B\n1,2\n'
        (d/name).write_bytes(data)
        (d/'active_dataset.json').write_text(json.dumps({'stored_name':name,'hash':hashlib.sha256(data).hexdigest()}))
        report=audit_dataset_library(root)
        assert report['active_integrity']=='PASS' and report['saved_file_count']==1
        (d/name).write_bytes(b'A,B\n3,4\n')
        assert audit_dataset_library(root)['active_integrity']=='HASH_MISMATCH'
        (d/'active_dataset.json').write_text(json.dumps({'stored_name':'../../private.csv'}))
        assert audit_dataset_library(root)['active_integrity']=='REVIEW_REQUIRED'
    print('PASS: Read-only Dataset Library recovery/integrity checks')
if __name__=='__main__':main()
