# Local Data Safety and Known Limitations

- Only `CSV` and `XLSX` uploads are accepted for the business Dataset Library; this release checks their extension, content, file size (256 MiB), and basic XLSX archive structure before Pandas parsing. This is **not** antivirus scanning or data de-identification.
- Stored dataset names are constrained to safe file basenames and cannot traverse directories or follow symlinks. Active dataset integrity is SHA-256 checked when a hash exists. Older metadata without hashes may still be read, but is marked as legacy in the audit.
- Original local `stored_datasets` is preserved; no automatic destructive migrations or background uploads occur.
- This local single-user architecture is not secure multi-user tenancy. Do not distribute it as a public service.
- Sensitive uploads can remain on local disk. The professor-review ZIP contains *no raw rows or original data values*; nevertheless inspect and selectively share any report containing customer/category labels.
- Financial calculations depend on properly mapped columns and user-confirmed completeness. They do not infer tax, operating expenses or invested capital not represented in the source.
- Market bootstrap/backtesting is historical research, not an AI trained calibrated forecast, live stock feed or guaranteed future result.
- This release tests 500k rows with real underlying modules optionally, including chart-data preparation and HTML report generation. Full browser rendering and all possible 500k interactions are **not** automatically tested.
- Dataset previews, quality scans, and charts can be set to large sizes; browser responsiveness depends on the chosen controls and available memory.
- Local start binds to 127.0.0.1. Other processes, firewall settings, remote desktop, browser plugins and OS permissions are outside this package's control.
