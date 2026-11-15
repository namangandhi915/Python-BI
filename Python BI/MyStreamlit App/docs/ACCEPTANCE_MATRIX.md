# Python BI Studio — Phase 4/5 Formal Acceptance Matrix

**Status:** Not yet formally signed off. The prior development work overlaps Phases 4 and 5 and is **substantially built**; this release provides automated evidence and a manual sign-off process.

| Area | Evidence available | What remains |
|---|---|---|
| Dashboard filtering | Explicit test fixtures plus real Dataset Library workflow | Check multi-date, missing-value, empty-filter, duplicate-index datasets in browser |
| Executive KPIs | Exact source/filtered financial reconciliation tests | Confirm selected fields/currency/unit in real datasets |
| Chart Studio | Existing six chart types and automated previous regressions | Browser rendering, tooltip/legend readability, small-screen accessibility |
| Category/period analysis | Category and calendar reconciliation fixtures | Multi-year/quarter datasets, negative revenue and category nulls in browser |
| Commercial mapping | Gross/net revenue, cost/profit arithmetic and invalid-data guards | Identify full accounting expense coverage, discounts/returns semantics |
| Profit/loss/ROI | Correct labels; net profit only after explicit confirmation | Validate accounting chart of accounts, non-additive capital and multi-currency data |
| Business Planning | Fixed/variable contribution and break-even scenarios | Approve assumptions and check model horizon in real business use cases |
| Investment Intelligence | NPV/IRR, stress and baseline backtesting tests | No calibrated predictive AI forecast or live market feed established |
| Excel and HTML reports | CSV formula guard and exported report reconciliation | Manual files, browser printing, privacy review and export retention policy |
| Large data | Real 500k Streamlit upload/search passed; cross-module benchmark offered | Full Streamlit cleaning, dashboard, charts, reports at representative 500k input; memory & latency acceptance thresholds |
| Theme/UX | Light corporate palette, consistent controls, collapsed panel | Final brand-wide typographic audit, accessibility evaluation and responsive behaviour |
| Deployment/security | Local code/tests, no cloud service needed | Authentication, authorisation, hosting, secrets review, deployment, backup/recovery and privacy testing |

## Approval rule

* Automated `PASS` means the defined fixture or static check passed.
* `MANUAL` means human browser, accounting, compliance or deployment acceptance is still required. It is not a failure, but **cannot be interpreted as completed**.
* `FAIL` means the release must not be accepted until fixed.

Do not copy a company's branding, proprietary assets or licensed fonts; the existing corporate theme is an original design informed by general enterprise design conventions.
