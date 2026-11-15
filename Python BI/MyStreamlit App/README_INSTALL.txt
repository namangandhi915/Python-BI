PYTHON BI STUDIO — NEXT COORDINATED DEVELOPMENT PACKAGE
Cross-phase Scale & Reliability — Combined Batches 1 + 2
=========================================================

PREVIOUS VERIFIED BASELINE
  Phase 3 Batches 1–14 complete; Phase 6 Foundation Batches 1–2 complete;
  Phase 6 Investment Stress/Bootstrap Batches 3–4 complete.
  This ZIP is based on that exact baseline, not on app(9).py.

WHAT THIS UPDATE DOES
  Batch 1: Search and filter the ENTIRE active dataset, then show a bounded
  preview (10–1000 rows). Full-data matching record counts, optional
  category/numeric filters, stable sort and clear full-dataset search labels.
  Batch 2: Bounded CSV exports (up to 50,000 rows, EXPLICITLY marked partial
  if truncated), opt-in exact quality checks for large inputs, measurable
  full-data Explorer computations, an isolated 10k/500k-row benchmark,
  and an optional generated 500k CSV for a real manual Streamlit upload test.
  All source datasets are unchanged by the computations.

EXACT FILE ACTIONS
  REPLACE: app.py ONLY (one Explorer block is wired to the new module).
  ADD: full_dataset_engine.py
  ADD: explorer_workspace.py
  ADD: benchmark_explorer.py
  ADD: test_scale_batch12.py
  ADD: test_explorer_ui_mock.py

  DO NOT REPLACE: investment_workspace.py, forecast_engine.py,
  forecast_panel.py, executive_dashboard.py, commerce_engine.py,
  bi_theme.css, Data/, stored_datasets/, .venv/ or .streamlit/.
  The new explorer_workspace.py imports the EXISTING audit_exports.py.

INSTALLATION IN VS CODE (WINDOWS)
  1. Open existing MyStreamlit App folder in VS Code.
  2. If Streamlit is running, Ctrl+C in its terminal.
  3. In the project root create ONE rollback folder:
       backup_before_scale_batch12
     Copy your CURRENT app.py into it. Do not move/delete the original.
  4. Download ZIP, Windows Downloads > Extract All, then open the extracted
     python_bi_scale_batch12 folder.
  5. Copy the SIX Python files above to MyStreamlit App project ROOT.
     Choose Replace for app.py. Other five files are new.
  6. No pip installs are required.

RUN AUTOMATED TESTS (ONE SESSION)
  In VS Code Terminal, from MyStreamlit App root:

    .\.venv\Scripts\Activate.ps1   [only if (.venv) not visible]
    python -m py_compile app.py full_dataset_engine.py explorer_workspace.py benchmark_explorer.py
    python test_scale_batch12.py
    python test_explorer_ui_mock.py
    python test_investment_foundation.py
    python test_investment_forecasting.py
    python test_phase3_batch2.py
    python test_phase3_batch34.py
    python test_phase3_batch56.py
    python test_phase3_batch78.py
    python test_phase3_batch910.py
    python test_phase3_batch1112.py
    python test_phase3_batch1314.py

  Successful new tests print:
    PASS: Entire-source search, bounded preview/export, filters, duplicates, source immutability, UI wiring
    PASS: Mocked Explorer UI controls, full-search count, preview and CSV export

RUN STREAMLIT
    python -m streamlit run app.py
  Open http://localhost:8501

ONE COMBINED BROWSER CHECK
  1. Home / Dataset Library / Dashboard still work.
  2. Data Workspace > Explore: Search all records, not merely first 100.
  3. Search for 'Laptop' in the 20-row practice workbook: matching row count
     and preview should agree with all matching rows.
  4. Category and numeric filters apply before preview, with correct results.
  5. CSV download opens in Excel with clean data; source is unchanged.
  6. Prepare & Validate / Commercial Intelligence still work.
  7. Investment Intelligence (both modes including new research sections) works.

OPTIONAL ISOLATED 500K BENCHMARK (DOES NOT CHANGE USER DATA)
  Stop server or open another VS Code terminal. Run:
    python benchmark_explorer.py --rows 10000
    python benchmark_explorer.py --rows 500000 --output benchmark_artifacts\benchmark_500k.json
  This ONLY benchmarks isolated Pandas Explorer operations, not Streamlit.

OPTIONAL REAL STREAMLIT UPLOAD TEST (CHANGES ACTIVE DATASET TEMPORARILY)
  1. From MyStreamlit App project root run:
    python benchmark_explorer.py --rows 500000 --emit-test-csv --output benchmark_artifacts\benchmark_500k.json
  2. Locate benchmark_artifacts\synthetic_explorer_500000.csv .
     This CSV has 500,000 synthetic records, 14 columns and a unique
     LAST-row Customer Name: SPECIAL-ROW-000499999.
  3. In Streamlit > Data Workspace > Explore, upload this CSV.
     Do NOT use your original business workbook to perform this stress test.
  4. Search for SPECIAL-ROW-000499999. Verify ONE full-source match,
     and a preview of that last row (beyond preview's first 100 rows).
     Check responsiveness, no crash and no unbounded preview.
  5. The upload becomes active and is saved to the existing Dataset Library.
     When finished, REACTIVATE your normal saved workbook from Dataset Library.
     Only after switching back, optionally delete the synthetic saved dataset.
     Never delete the real business dataset.
  6. This is a browser-level smoke test for UPLOAD + EXPLORE, NOT proof that
     every Dashboard, report and cleaning feature scales to 500,000 rows.

LIMITS AND CAVEATS
  - CSV downloads are capped at 50,000 matching rows; if more match,
    the UI explicitly warns that it is a PARTIAL export.
  - Full-data searches scan selected columns in 20k-row chunks. Full
    matching record counts are correct, but filtering/sorting can still cost
    CPU/memory with very large or high-cardinality datasets.
  - For large datasets, exact missing/duplicate quality counts are opt-in.
  - This package is NOT the final website-wide 500k performance or
    security/deployment certification.
  - If you edited your local app.py after Phase 6 Batch 4, compare it with
    this package before replacing it; keep your backup for rollback.

NEXT PRIORITIES
  Full-website scalable workflows and acceptance review of Phases 4/5,
  enterprise-wide visual redesign, production readiness/deployment.
