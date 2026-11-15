# Python BI Studio

A local Streamlit business intelligence application for exploring datasets,
building dashboards, comparing periods, and reviewing financial metrics.

## Run locally

From the project directory:

```powershell
cd "Python BI/MyStreamlit App"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python start_local.py
```

Then open <http://127.0.0.1:8501>. The launcher binds to loopback and does not
deploy the app publicly. See [the app guide](Python%20BI/MyStreamlit%20App/README_INSTALL.md)
and [operating docs](Python%20BI/MyStreamlit%20App/docs/) for details.

## Verify

From `Python BI/MyStreamlit App`, run:

```powershell
python verify_final_release.py
python run_final_acceptance.py --rows 10000
```

The automated acceptance command uses synthetic data and writes local evidence
under `acceptance_results/`. Browser and real-data acceptance are separate
manual checks documented in `docs/05_GATE_BROWSER_CHECKLIST.md`.
