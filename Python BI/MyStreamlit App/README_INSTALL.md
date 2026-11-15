# Install, run, and verify

The project has one Streamlit entry point, `app.py`. Supporting code is in
`modules/`; automated tests are in `tests/`; command-line tools are in
`scripts/`; data assets are in `data/`; and CSS is in `assets/`.

## Windows setup

Run these commands from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python start_local.py
```

Open <http://127.0.0.1:8501>. The app binds to the local computer only. Stop it
with `Ctrl+C` in the terminal.

## Automated checks

```powershell
python scripts/verify_final_release.py
python scripts/run_final_gate_tests.py
python scripts/run_final_acceptance.py --rows 10000
```

The checks use synthetic data and write disposable output beneath `outputs/`.
Complete browser checks separately using `docs/05_GATE_BROWSER_CHECKLIST.md`.
