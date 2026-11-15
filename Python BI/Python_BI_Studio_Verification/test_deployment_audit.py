from pathlib import Path
from tempfile import TemporaryDirectory
from deployment_audit import check_deployment, release_gate, SENSITIVE_EXCLUSIONS
from prepare_privacy import add_ignores


def main():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / '.streamlit').mkdir()
        (root / '.streamlit' / 'config.toml').write_text('[theme]\nbase="light"\n')
        (root / '.gitignore').write_text('stored_datasets/\n')
        report = check_deployment(root)
        assert release_gate(report) == 'BLOCKED_FOR_PUBLIC_DEPLOYMENT'
        assert sum(x['status']=='BLOCKED' for x in report) >= 3
        assert any(x['id']=='PRIVATE-GIT' and x['status']=='REVIEW' for x in report)
        changed, missing = add_ignores(root)
        assert changed and 'stored_datasets/' not in missing
        assert all(x in (root/'.gitignore').read_text() for x in SENSITIVE_EXCLUSIONS)
        changed2, _ = add_ignores(root)
        assert not changed2
        assert any(x['id']=='PRIVATE-GIT' and x['status']=='PASS' for x in check_deployment(root))
        assert (root/'.gitignore').read_text().count('stored_datasets/')==1
    print('PASS: Public release gate, shared-storage blockers, append-only privacy rules, idempotence')

if __name__=='__main__':main()
