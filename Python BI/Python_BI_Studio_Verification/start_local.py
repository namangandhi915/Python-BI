"""Launch the existing Streamlit app on loopback only. Does NOT deploy to cloud."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys


def command(root: Path):
    app = Path(root) / 'app.py'
    if not app.is_file():
        raise FileNotFoundError('app.py must exist in the project root.')
    return [sys.executable, '-m', 'streamlit', 'run', str(app),
            '--server.address', '127.0.0.1', '--server.port', '8501',
            '--browser.gatherUsageStats', 'false']


def main():
    root = Path(__file__).resolve().parent
    print('LOCAL MODE ONLY: http://127.0.0.1:8501 (no public deployment)')
    return subprocess.call(command(root),cwd=root)

if __name__ == '__main__':
    raise SystemExit(main())
