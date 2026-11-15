# Operations runbook

## Start the app

Open a terminal in `Python BI/MyStreamlit App` and run:

```powershell
.\.venv\Scripts\Activate.ps1
python start_local.py
```

The app is available at <http://127.0.0.1:8501>. Stop it with `Ctrl+C`.

## Project folders

- `modules/`: business, finance, reporting, and UI modules
- `tests/`: automated regression and acceptance tests
- `scripts/`: launch support, verification, and reporting commands
- `assets/`: theme stylesheet
- `data/`: sample workbook and synthetic fixtures
- `docs/`: operating, accounting, and acceptance guides
- `manifests/`: SHA-256 integrity records
- `outputs/`: regenerable local test and release reports

## Verify changes

```powershell
python scripts/verify_final_release.py
python scripts/run_final_gate_tests.py
python scripts/run_final_acceptance.py --rows 10000
```

These checks do not replace the browser and real-data review in
`05_GATE_BROWSER_CHECKLIST.md`. Keep user datasets under `stored_datasets/` and
back them up separately before testing recovery procedures.
