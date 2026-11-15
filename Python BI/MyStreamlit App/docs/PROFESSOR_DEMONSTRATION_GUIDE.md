# Python BI Studio — Professor Demonstration Guide

## Format

Private local demonstration in VS Code + Chrome, not a hosted website. Use `python start_local.py`, navigate to `http://127.0.0.1:8501`, and keep datasets under your control. Professor approval must be documented manually.

## Suggested walkthrough (approx. 15–25 minutes, flexible)

1. **Opening / purpose (2 min):** One connected enterprise-style BI platform for inspection, cleaning, commerce and investment research.
2. **Home / design (2 min):** Show the executive light interface and existing navigation; no separate professor-named website panel is added.
3. **Dataset management (2 min):** Restore named saved workbook, switch datasets, explain safe deletion and permanent local storage.
4. **Explore / Prepare (3 min):** Search entire dataset; show missing values, two-column comparison and export.
5. **Commercial analytics (4 min):** Map correct revenue/cost fields, distinguish mapped-cost profit from accounting net profit; show business planning.
6. **Executive Dashboard (4 min):** Compare charts, filters, category mix, report centre and Excel/HTML/ZIP exports.
7. **Investment Intelligence (3 min):** Separate business NPV/IRR scenarios from historical market volatility, bootstrap and backtests; do not call these guaranteed predictions.
8. **Quality and next steps (3 min):** Show multi-sector synthetic acceptance, 500k row tests and remaining limitations.

## Materials to prepare

- Run the local combined regression suite; keep `professor_results/LOCAL_TEST_RESULTS.json`.
- Run `python local_review_cli.py --rows 10000` and `python create_demo_datasets.py --rows 120`.
- If useful, inspect the optional offline `professor_results/PROFESSOR_REVIEW_PACKET.zip` before the meeting; no website panel or extra navigation is required.
- Record actual performance figures from your laptop if comparing devices; do not reuse benchmark timings as universal guarantees.
- Ask the professor to evaluate **functionality, correctness, interface, methodology, limitations and documentation**.

## Caution

Review packets include no transaction-level data. Only demonstrate the original business workbook if you have permission to share it. The synthetic datasets are safe demonstrations because their entities and values are fictional. Do not publish a URL or change hosting settings.
