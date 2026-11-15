# Public deployment is blocked — security gates

**Do not deploy this iteration as an open multi-user web service.** The current Dataset Library stores uploaded files, labels and `active_dataset.json` in a project-wide directory. Multiple unauthenticated visitors could overwrite or access shared state. Production readiness reports intentionally retain a `BLOCKED_FOR_PUBLIC_DEPLOYMENT` gate.

To clear the gate in a *future* release:

1. **Authentication and authorisation:** Verify each user and enforce per-user dataset access in every uploader, listing, export, switch and deletion path. A cosmetic login screen is not sufficient.
2. **Storage isolation:** Replace `stored_datasets` and global `active_dataset.json` with user-/tenant-scoped storage, protected identifiers and permissions. Confirm cross-user access is impossible with adversarial tests.
3. **Durable persistence:** Use a managed, backed-up store with retention, deletion and restore policies. Ephemeral cloud file systems are unsuitable for durable user libraries.
4. **Privacy:** Review customer names, identifiers, source workbooks, CSV exports and ZIP reports. Never publish real customer-level data as demo assets.
5. **Repository:** Ensure `.venv`, `stored_datasets`, `Data`, `.streamlit/secrets.toml`, `.env`, benchmark CSVs and release reports are excluded from Git. Check `git ls-files` and repository history: `.gitignore` does not remove previously committed files.
6. **Secrets:** Configure remote secrets in deployment settings; never commit plaintext credentials. The preflight reports no secret values.
7. **Controls:** Add upload size and compute budgets, timeout policies, monitoring, incident response, XSRF/CORS review and real-browser security/scale tests.
8. **Dependency review:** Use pinned versions tested on the exact deployment Python version; include a software dependency vulnerability review.

Streamlit Community Cloud currently documents `requirements.txt`/other supported dependency managers, deployment secret settings, and `.streamlit/config.toml` at the project root. See https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies and https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management . These official instructions do **not** eliminate the architecture's isolation issues.

`python release_cli.py` generates an audit snapshot without accessing user rows; it does not deploy or grant approval. `python prepare_privacy.py` modifies only `.gitignore` by appending rules. `python dependency_snapshot.py` writes a candidate pinned dependency list only when explicitly run and does not overwrite an existing candidate unless `--overwrite` is provided.
