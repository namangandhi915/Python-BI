# Python BI Studio

A local Streamlit business intelligence app for exploring data, building
dashboards, comparing periods, and reviewing financial metrics.

## Project layout

All app files live under `Python BI/MyStreamlit App/`:

```text
MyStreamlit App/
├── app.py, start_local.py, requirements.txt
├── modules/       reusable application code
├── tests/         regression and acceptance tests
├── scripts/       verification, release, and data-generation commands
├── assets/        CSS and visual resources
├── data/          workbook, demos, and sample files
├── docs/          user and operations guides
├── manifests/     file integrity manifests
├── reports/       checked-in report data
└── .streamlit/    Streamlit configuration
```

## Run locally

From the repository root:

```powershell
cd "Python BI/MyStreamlit App"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python start_local.py
```

Open <http://127.0.0.1:8501>. The launcher listens on loopback and does not
deploy the app publicly. See the [app guide](Python%20BI/MyStreamlit%20App/README_INSTALL.md)
and [operating docs](Python%20BI/MyStreamlit%20App/docs/) for details.

## Verify

From `Python BI/MyStreamlit App`, run:

```powershell
python scripts/verify_final_release.py
python scripts/run_final_gate_tests.py
python scripts/run_final_acceptance.py --rows 10000
```

These automated checks use synthetic data. Browser and real-data checks remain
manual; see `docs/05_GATE_BROWSER_CHECKLIST.md`.
