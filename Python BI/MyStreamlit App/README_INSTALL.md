# Install and run

Python BI Studio runs locally with Streamlit.

## Windows

Open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python start_local.py
```

Open <http://127.0.0.1:8501>. To stop the app, press `Ctrl+C` in the
terminal. `start_local.py` listens only on the local computer.

## Checks

```powershell
python verify_final_release.py
python run_final_acceptance.py --rows 10000
```

Acceptance checks use synthetic data and create local evidence in
`acceptance_results/`. Complete the browser checks in
`docs/05_GATE_BROWSER_CHECKLIST.md` separately; automated checks do not certify
real data mappings or browser behavior.
