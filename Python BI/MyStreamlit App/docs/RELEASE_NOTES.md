# Release notes — Enterprise Design & Release Readiness 1

Baseline: user-confirmed Enterprise Assurance release, all 12 browser checks passed.

### Changed
- `app.py`: imports two optional display helpers, replaces duplicate generic top heading with context-aware page masthead; adds one collapsed Home release panel.
- `assets/bi_theme.css`: replaces accumulated per-batch overrides with one light, responsive, token-driven stylesheet and retains original Home components.

### Added
- `modules/design_system.py`: escaped four-mode page masthead; safe active dataset name.
- `modules/deployment_audit.py`: conservative, non-sensitive local deployment checks and non-negotiable security blockers.
- `modules/operations_ui.py`: collapsed Home readiness dashboard.
- `modules/release_evidence.py` / `scripts/release_cli.py`: static JSON, HTML and aggregate ZIP summaries without transaction rows.
- `scripts/dependency_snapshot.py`: opt-in direct dependency version snapshot.
- `scripts/prepare_privacy.py`: optional append-only .gitignore privacy improvement.
- `scripts/run_design_release_tests.py`: one full regression command and summary JSON.
- New tests, deployment documentation and versioned SHA-256 installation verifier.

### Not changed
- Dataset Library storage format, user files and labels.
- Commercial or financial calculation formulas.
- Dashboard/Chart Studio/report engines.
- Investment scenario calculations and forecasting research.
- Streamlit config.toml (retains your chosen light theme).

### No claims of completion
- Does not implement authentication, tenant isolation, managed persistence, live data providers, a calibrated ML investment forecast, or production deployment.
- Does not establish end-to-end 500,000-row browser throughput for every module.
