# VS Code operations runbook — Windows

## Start work
1. Open VS Code and **File → Open Folder → MyStreamlit App**.
2. Terminal → New Terminal; if `(.venv)` is not displayed, `\.venv\Scripts\Activate.ps1`.
3. Run `python -m streamlit run app.py`; open http://localhost:8501.
4. Confirm Dataset Library shows the original business workbook (20 records, 14 columns), if that is your intended active dataset.

## Stop safely
1. Save All (`Ctrl+K`, then `S`) in VS Code.
2. Stop the terminal process with `Ctrl+C`.
3. Close browser, Excel and VS Code after saving any manual changes.
4. Never delete `stored_datasets`, `.venv`, `Data`, or the most recent backup folder during routine shutdown.

## Offline verification, one batch
1. In the project terminal, run `python verify_design_release.py`.
2. Run `python run_design_release_tests.py` (full previous regression suite; no Streamlit browser needed).
3. Run `python release_cli.py` (generates minimal offline JSON, HTML, ZIP readiness evidence).
4. Run `python run_enterprise_assurance.py --rows 10000` if reviewing the old acceptance report too.
5. Restart Streamlit and perform the 12-point browser review in `RELEASE_ACCEPTANCE.md`.

## Rollback
If the new release introduces a runtime error, stop Streamlit, then restore ONLY the replaced `app.py` and `bi_theme.css` from `backup_before_design_release`. New Python helpers may remain unused. Never roll back the Dataset Library or delete business data to troubleshoot a design change.
