# Five final acceptance gates — one local browser session

**Purpose:** Close the original Python BI Studio local-development roadmap, not to host the website or obtain professor approval inside the application.

**Before testing:** Keep a backup of `app.py`, `modules/commerce_engine.py` and your `stored_datasets` folder. Activate your original **Python BI – Business Transactions 2026** dataset before beginning. Launch using `python start_local.py` at `http://127.0.0.1:8501`. For server-side render timings, optionally start with `$env:PYTHON_BI_UI_METRICS="1"` in PowerShell *before* `python start_local.py`.

## Gate 1 — Dashboard compatibility / multi-schema

- [ ] On original 20x14 workbook, **Dashboard → Detailed Analytics (Legacy)** opens as before. Verify Sales, Total Cost, Profit and margin reconcile with Excel; no fallback warning on the original valid dataset.
- [ ] **Dashboard → Executive Overview** loads and its category/period filters work on that workbook.
- [ ] Upload `data/demo/FAKE_retail_120.csv`, then switch to **Dashboard → Detailed Analytics (Legacy)**: you should see a compatibility warning and an explicitly mapped, bounded alternative, NOT a broken or falsely labelled legacy dashboard.
- [ ] In compatible view, map `GrossSales` and `CostOfGoods` (these are gross and cost-of-goods only; see accounting cautions); check metrics and safe audit download. The primary Executive Overview should also work with appropriate mappings.
- [ ] Repeat relevant Executive Overview/category/period checks with `FAKE_services_120.csv` (`ServiceFees`, `DeliveryCosts`) and `FAKE_manufacturing_120.csv` (`InvoiceValue`, `ProductionCost`). Missing fields must never be silently replaced by unrelated ones.
- [ ] Apply an empty-result filter, then restore normal filters. No exception, fake result or abandoned selection should appear.

## Gate 2 — Realistic financial accounting / reconciliations

- [ ] In **Data Workspace → Commercial Intelligence**, map revenue, costs, discounts, returns, operating expenses and taxes for each synthetic sector fixture using the field names in `docs/ACCOUNTING_ASSUMPTIONS.md`.
- [ ] Confirm `Net Revenue = Gross Revenue − Discounts − Returns` and `Profit after Mapped Costs = Net Revenue − Cost of Sales − Operating Expenses − Taxes`. Compare at least three source rows and totals in Excel.
- [ ] Confirm **Net Profit** appears only after explicitly confirming all relevant costs are included; ROI requires a meaningful, additive invested-capital field.
- [ ] Check that missing/invalid financial values visibly block misleading calculations instead of being treated as zero. The automated suite covers zero revenue, negative numbers, overlapping field roles, and invalid numeric inputs.
- [ ] When available, verify ONE representative **real** business dataset's column definitions (gross vs net sales, currency, returns, cost recognition, taxes). Do not enter assumptions or claim real-accounting sign-off when definitions are unavailable.

## Gate 3 — Full Streamlit application performance

- [ ] Generate synthetic files with `python scripts/build_acceptance_test_data.py --rows 10000 100000` and optionally `--rows 500000`; the 500k CSV may consume substantial laptop RAM and disk.
- [ ] Open **Data Workspace → Explore**, upload the 10k fixture, search for `SPECIAL-ROW-000009999`, note the real browser response and full-source match count of 1. Save/switch datasets as appropriate.
- [ ] Repeat the search for 100k `SPECIAL-ROW-000099999`; optionally 500k `SPECIAL-ROW-000499999` where your system permits. The preview limit must not replace the full-source search.
- [ ] With at least 100k rows active, test **Executive Dashboard**, **Chart Studio** and **Prepare & Validate** (at least one reasonable operation), plus **Executive Report Centre / HTML/ZIP** where supported by selected fields. Record actual wall-clock response times, failures, any browser freezes and memory constraints. Do not assume timings are acceptable because module-chain benchmarks pass.
- [ ] While the 100k/500k dataset is active, try **Detailed Analytics (Legacy)** and confirm it redirects rather than attempting an unlimited old tutorial workflow.
- [ ] With Streamlit stopped after the run, execute `python scripts/summarize_browser_timings.py`. This file measures **selected server-side render functions**, not Chrome paint/download time or the entire cleaning page. Use your manual stopwatch notes too.

## Gate 4 — Reliability, exports and local recovery

- [ ] Confirm empty/missing categories, invalid/missing dates, negative values and user-empty filters do not create false financial figures (see test fixtures).
- [ ] Download financial CSV and HTML/ZIP reports; open them in Excel/browser and reconcile **displayed KPI totals** to the exports. Spreadsheet-formula-looking text must remain text.
- [ ] Temporarily stop Streamlit with `Ctrl+C`, restart using `python start_local.py`, confirm the active original business workbook, Dataset Library labels and navigation persist.
- [ ] Confirm that changing between demo datasets never destroys the original saved workbook. Restore it after testing.
- [ ] No `.venv`, `stored_datasets`, workbook, or credentials should be deleted or overwritten by installing this update.

## Gate 5 — Local technical closure (not academic approval)

- [ ] `python scripts/verify_final_release.py` passes all installed SHA-256 checks.
- [ ] `python scripts/run_final_gate_tests.py` passes all automated suites with zero failures.
- [ ] `python scripts/run_final_acceptance.py --rows 10000` generates the JSON, HTML and ZIP evidence. Optionally re-run at 100k and 500k; the last report overwrites the previous summary, so save versions if comparing.
- [ ] Confirm the evidence report says **AUTOMATED_PASS__MANUAL_ACCEPTANCE_PENDING** until manual checks are truly verified. Do not treat the generated report as professor approval.
- [ ] Record any limitations in your external notes: trained/calibrated AI return forecasting and live-market provider data are not implemented; multi-user public hosting is outside the approved local scope.
- [ ] Keep the final website **local-only** at `http://127.0.0.1:8501`. No professor-named section should exist.

**Sign-off:** Only after all applicable manual checks are actually successful may you confirm local technical acceptance. The project remains subject to your professor's separate assessment and future instructions.
