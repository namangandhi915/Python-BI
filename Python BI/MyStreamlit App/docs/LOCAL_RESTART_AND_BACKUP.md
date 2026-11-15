# Local install and restart

The app is launched from the `MyStreamlit App` folder. Keep local datasets in
`stored_datasets/`; the example workbook and synthetic fixtures live in
`data/`.

## Start and stop

```powershell
.\.venv\Scripts\Activate.ps1
python start_local.py
```

Open <http://127.0.0.1:8501>. Stop the server with `Ctrl+C` in that terminal.

## Verify after an update

From the project folder:

```powershell
python scripts/verify_final_release.py
python scripts/run_final_gate_tests.py
python scripts/run_final_acceptance.py --rows 10000
```

The final command writes reports to `outputs/acceptance_results/`. Test suites,
scripts, reusable modules, static assets, and manifests live in their own
folders; see `../../README.md` for the project map.

## Preserve local data

Back up `stored_datasets/` separately before changing the app. Automated checks
use temporary or synthetic data and do not replace the active dataset. Browser
and real-data checks remain manual as described in
`05_GATE_BROWSER_CHECKLIST.md`.
