"""Offline, read-only project configuration inspection. No secrets or paths exported."""
from __future__ import annotations
from pathlib import Path
import ast
import importlib.metadata
import sys

CORE = ('app.py','modules/commerce_engine.py','modules/quality_engine.py','modules/executive_dashboard.py',
        'modules/explorer_workspace.py','modules/full_dataset_engine.py','modules/investment_workspace.py',
        'modules/investment_engine.py','modules/forecast_engine.py','modules/report_engine.py',
        'assets/bi_theme.css')


def inspect_project(root: Path) -> list[dict]:
    checks = []
    for name in CORE:
        present = (root / name).is_file()
        checks.append({'id': f'FILE:{name}', 'area': 'Project completeness',
                       'status': 'PASS' if present else 'FAIL',
                       'detail': 'Present' if present else 'Required file absent'})
    config = root / '.streamlit' / 'config.toml'
    if config.exists():
        try:
            import tomllib
            theme = tomllib.loads(config.read_text(encoding='utf-8')).get('theme',{})
            correct = theme.get('base') == 'light'
            checks.append({'id':'THEME','area':'Project configuration',
                           'status':'PASS' if correct else 'MANUAL',
                           'detail':'Light theme set' if correct else 'Review light-theme setting'})
        except Exception:
            checks.append({'id':'THEME','area':'Project configuration','status':'MANUAL',
                           'detail':'Unable to parse theme config'})
    else:
        checks.append({'id':'THEME','area':'Project configuration','status':'MANUAL',
                       'detail':'No .streamlit/config.toml in this installation'})
    for name in ('app.py', 'modules/executive_dashboard.py', 'modules/investment_workspace.py'):
        target=root/name
        if target.exists():
            try:
                ast.parse(target.read_text(encoding='utf-8'))
                status='PASS'; detail='Python syntax valid'
            except (SyntaxError, UnicodeError):
                status='FAIL'; detail='File failed Python parsing'
            checks.append({'id':'AST:'+name,'area':'Project syntax','status':status,'detail':detail})
    for package in ('pandas','numpy','plotly','streamlit','openpyxl'):
        try:
            version = importlib.metadata.version(package)
            status, detail = 'PASS', f'Installed, version {version}'
        except importlib.metadata.PackageNotFoundError:
            status, detail = 'FAIL', 'Not installed in the active interpreter'
        checks.append({'id':'DEPENDENCY:'+package,'area':'Environment',
                       'status':status,'detail':detail})
    checks.append({'id':'PYTHON','area':'Environment','status':'PASS',
                   'detail':f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'})
    return checks
