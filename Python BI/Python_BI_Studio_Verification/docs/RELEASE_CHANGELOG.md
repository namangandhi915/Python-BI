# Final Roadmap Acceptance & Closure — changes

- Two replacements: `app.py` (existing UI intact; added schema-aware Detailed Analytics fallback and opt-in page render instrumentation), `commerce_engine.py` (prevents silently ignoring operating expenses/taxes when no cost-of-sales field is mapped; detects duplicate source columns).
- New `schema_aware_dashboard.py` checks legacy columns, types, profit and margin consistency, dates, zero sales and maximum row count; keeps original workbook's detailed view unchanged.
- New `ui_runtime_metrics.py` and `summarize_browser_timings.py` measure selected Streamlit server-side render functions only with opt-in flag; no dataset names, values or usernames in generated timing logs.
- New `final_financial_checks.py`, `final_reliability_checks.py`, `run_final_gate_tests.py` and final tests provide 23+ non-destructive financial/reliability acceptance checks and preserve regression coverage.
- New `build_acceptance_test_data.py` makes fake 14-field 10k/100k/500k CSVs without activating/saving anything in Dataset Library.
- New `run_final_acceptance.py` creates sanitized local JSON, HTML and ZIP evidence under `acceptance_results`; keeps browser/manual sign-off pending.
- No professor-specific website section, cloud hosting, user management or modification of saved business datasets.
