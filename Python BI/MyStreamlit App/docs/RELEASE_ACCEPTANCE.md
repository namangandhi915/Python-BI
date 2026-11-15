# Enterprise Design & Release Readiness — manual acceptance

## Browser checks (one combined review)
1. Home displays masthead, polished hero, current dataset status and feature cards.
2. Sidebar shows four main pages and retains the Dataset Library selection, safe activation, labels and deletion controls.
3. Home's **Platform assurance · dataset health** remains operational, with sampled/exact scope correctly labelled.
4. Home's **Release readiness · privacy & deployment** shows the blocked public gate, statuses and downloadable ZIP evidence.
5. Data Workspace → Explore searches the full dataset; category/numeric filters, bounded preview, export and exact quality still function.
6. Prepare & Validate retains missing-value inspector, comparison, cleaning, validation, before/after and download.
7. Commercial Intelligence → Financial Performance uses mapped fields and reconciled totals.
8. Commercial Intelligence → Business Planning displays scenarios and break-even results.
9. Dashboard → Executive Overview charts, Section 07 Chart Studio and Section 08 Performance Lab work.
10. Dashboard → Section 09 report pack ZIP, Section 10 category mix and clean CSV exports work.
11. Investment Intelligence → Business Investment Decisions retains NPV/IRR scenarios and downside/base/upside stress testing.
12. Investment Intelligence → Financial Markets accepts an appropriate SMALL synthetic market CSV and retains chart, historical bootstrap and backtest. The 57 MB business benchmark CSV is intentionally invalid for this 25 MiB market importer.
13. Responsive review: keyboard navigation, text size, 125–150% browser zoom, narrow viewport and focus outlines.
14. Dataset Library reactivation restores the original business workbook; no data loss or unintentional original-data mutation.

## Status accounting
- Automated tests and offline preflight can pass **while public deployment remains blocked**.
- The 500,000-row Explorer upload/search was user-verified in the previous Scale release; a complete 500,000-row Dashboard + report workflow remains a separate future test.
- Phases 4 and 5 require additional manual finance dataset acceptance before being formally signed off.
- Historical bootstrap simulation is statistical research, not a trained AI return forecast or a guaranteed return.
