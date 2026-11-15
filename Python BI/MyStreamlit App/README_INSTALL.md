# Python BI Studio — Final Roadmap Acceptance & Closure

**Target baseline:** the **corrected Local Roadmap Validation** update that the user confirmed passed all **18** browser checks. This is one coordinated local-only upgrade. The original four-page Streamlit website and Dataset Library remain intact. No public hosting.

## Installation (VS Code only)

1. Stop Streamlit with `Ctrl+C`.
2. In your `MyStreamlit App` folder create `backup_before_final_acceptance`. Copy the existing `app.py` and `commerce_engine.py` into this backup folder. Do not move/delete originals. Optionally copy `stored_datasets` to a separate backup without changing active files.
3. Download and **Extract All** from this ZIP. Open the extracted folder `python_bi_final_acceptance_release`.
4. Copy all root-level `.py` files **plus `FINAL_ACCEPTANCE_MANIFEST.json`** into the existing `MyStreamlit App` root. When Windows asks, replace **only `app.py` and `commerce_engine.py`**. All other source files are additions. Merge the `docs` folder with your existing project docs.
5. Preserve your previous `.venv`, `.streamlit`, `Data`, `stored_datasets`, `bi_theme.css`, Dashboard/report/investment modules, and original workbook. **Do not copy the whole extracted folder as a nested folder inside the project.**

## Single terminal automated check (PowerShell in VS Code)

```powershell
.\.venv\Scripts\Activate.ps1
python verify_final_release.py
python run_final_gate_tests.py
python run_final_acceptance.py --rows 10000
python build_acceptance_test_data.py --rows 10000 100000
```

New regression runner should finish with **zero failed test scripts**, and the CLI should create `acceptance_results/FINAL_ACCEPTANCE_REPORT.json`, `.html` and `FINAL_ACCEPTANCE_EVIDENCE.zip`. Synthetic 14-field CSVs appear in `acceptance_artifacts`. The final report should intentionally say `AUTOMATED_PASS__MANUAL_ACCEPTANCE_PENDING`, not prematurely approved.

If a run fails, copy the **first actual error** from the VS Code terminal. Do not proceed to browser sign-off until corrected. The prior `verify_local_release.py` checksums pertain to an older release and are expected to fail after replacing `app.py`; use the new verifier.

## Local-only launch and optional server timing

```powershell
$env:PYTHON_BI_UI_METRICS="1"
python start_local.py
```

Open `http://127.0.0.1:8501`. This flag is optional: without it the app remains fully functional but does not write selected page render timings. The timing data in `acceptance_results/ui_server_timings.jsonl` contains only predefined page identifiers, row/column counts, durations, process memory and errors' **class names**. No dataset values, names or user identifiers. It does **not** capture Chrome rendering or full cleaning-page duration.

For full browser acceptance follow **`docs/05_GATE_BROWSER_CHECKLIST.md`**. Check original workbook legacy Detailed Analytics, three FAKE sectors, 10k/100k (and optional 500k if laptop resources allow), realistic finance, downloads, restart/recovery and the unchanged Investment Intelligence modes. Optionally generate 500k test CSV with:

```powershell
python build_acceptance_test_data.py --rows 500000
```

If 500k is too demanding for your PC, record its hardware limitation. Do not force a failed/unresponsive session or misrepresent that test as passed. **Restore the original 20×14 workbook at the end** via Dataset Library.

After stopping Streamlit, optionally summarise selected server-side timings:

```powershell
python summarize_browser_timings.py
python run_final_acceptance.py --rows 10000
```

Run the CLI again at the end to include any available timing summary in the evidence ZIP. If you want to benchmark module-chain performance separately at greater row counts:

```powershell
python run_final_acceptance.py --rows 100000
python run_final_acceptance.py --rows 500000
```

These commands use synthetic records and may temporarily use substantial RAM. They overwrite the standard report output; save copies externally if comparing runs.

## What is and is not complete

- **Automated:** Legacy schema guard, independent financial arithmetic, sector fixtures, spreadsheet/HTML export safety, temporary-library recovery tests, module-chain scale check, previously verified calculations and new integrity manifest.
- **Browser / manually pending:** Real Streamlit workloads, actual Chrome response, restoration from real saved datasets, real financial column definitions, final project sign-off.
- **Out of scope:** cloud deployment, public URLs, multi-user login and professor-related website sections. Trained AI forecasting/live market integration must not be represented as finished.

The installation rollback is documented in `docs/LOCAL_RESTART_AND_BACKUP.md`. Do not delete real datasets to test recovery.
