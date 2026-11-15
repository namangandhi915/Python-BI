# Safe local workflow — Windows / VS Code

1. Before installing the final acceptance overlay, stop Streamlit with `Ctrl+C`.
2. Back up `app.py` and `commerce_engine.py` in a new folder `backup_before_final_acceptance`. They are the only existing source files replaced. Optionally copy the entire `stored_datasets` folder to a separate safe location without deleting or modifying originals.
3. Copy the final ZIP's root `.py` files and `FINAL_ACCEPTANCE_MANIFEST.json` into `MyStreamlit App`. Replace exactly `app.py` and `commerce_engine.py` when prompted; all other files are new. Merge the ZIP's `docs` folder with your existing `docs` folder.
4. In VS Code Terminal, activate `.venv`: ` .\.venv\Scripts\Activate.ps1 ` (without surrounding spaces).
5. Verify `python verify_final_release.py`, run tests `python run_final_gate_tests.py`, generate report `python run_final_acceptance.py --rows 10000`.
6. For optional local server timings, set `$env:PYTHON_BI_UI_METRICS="1"` in **the same** VS Code PowerShell terminal. Start locally with `python start_local.py` (host 127.0.0.1, port 8501).
7. Stop using `Ctrl+C`; if needed clear the optional variable with `Remove-Item Env:PYTHON_BI_UI_METRICS`.
8. After testing FAKE sector/large files, select your saved **Python BI – Business Transactions 2026** workbook in Dataset Library and click **Activate Selected Dataset**. Verify 20 rows × 14 columns.
9. If a new update breaks the local app, stop Streamlit, restore the two backed-up files from `backup_before_final_acceptance`, and start `python start_local.py` again. New helper files may remain unused; do not delete `stored_datasets`.

**Important:** Never run earlier `verify_local_release.py` or `verify_design_release.py` to validate this newer `app.py`; their checksums belong to superseded releases. Use `verify_final_release.py`.
