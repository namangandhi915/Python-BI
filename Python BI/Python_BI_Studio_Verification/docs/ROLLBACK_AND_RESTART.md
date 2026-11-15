# Restart / Rollback (VS Code on Windows)

1. Stop Streamlit in its VS Code terminal with **Ctrl+C**.
2. To roll back only the new integration, copy `backup_before_professor_local_release/app.py` back to the original project root, replacing `app.py`.
3. Leave all existing datasets and other modules in place.
4. If VS Code was closed, reopen the existing `MyStreamlit App` folder, open a new terminal, run `.\.venv\Scripts\Activate.ps1` only if not already activated.
5. Start **locally** with `python start_local.py` (or `python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501`).
6. Open `http://127.0.0.1:8501`. Confirm the active dataset is the correct workbook.

The new files remain dormant after rollback; they do not modify `stored_datasets` by themselves.
