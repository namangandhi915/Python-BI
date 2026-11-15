# Restart and rollback

## Restart locally

1. Stop Streamlit in its terminal with **Ctrl+C**.
2. Reopen the `MyStreamlit App` folder and start a terminal there.
3. Activate `.venv` if it is not already active: `.\.venv\Scripts\Activate.ps1`.
4. Run `python start_local.py` and open <http://127.0.0.1:8501>.

## Roll back a code change

Use Git from the repository root to inspect the history and restore the files from the chosen commit. For example, `git log --oneline` lists recent commits and `git restore --source=<commit> -- "Python BI/MyStreamlit App/app.py"` restores the app entry point. Replace the path with the file or folder being restored, then review `git status` before committing the rollback.

Keep `stored_datasets/` and `data/` intact when rolling back application code. The app does not modify stored datasets during startup.