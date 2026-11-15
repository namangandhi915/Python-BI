# Security, privacy and evidence limits

This is a **local development release** and does not certify production security, regulated financial compliance or investment suitability.

- `scripts/run_enterprise_assurance.py` uses deterministic synthetic input unless a test-specific CSV is explicitly supplied. It never updates `stored_datasets/` or `data/business/`.
- The Home assurance download includes only column names, data types and missing-count statistics; column names themselves could be sensitive, so review before sharing.
- The SHA-256 manifest checks file integrity against the packaged release. It is not a signed supply-chain attestation and cannot distinguish an independently modified copy from a maliciously replaced package.
- Full-source missing/duplicate scans are opt-in and can consume resources on large datasets. Sampled counts must not be represented as exact full-source counts.
- Financial results rely on user-defined mappings, accounting conventions and one consistent currency. Missing charges and account balances are not silently inferred.
- Investment bootstrap scenarios are historical resampling experiments, **not calibrated confidence intervals or guaranteed future returns**.
- The benchmark is the real module chain but **not** an end-to-end Streamlit performance certification. Browser memory, serialisation, multiple users, chart rendering, and export generation are not included.
- If deploying online, explicitly implement authentication/authorisation and a private storage policy before exposing business data. Nothing in this package implements multi-user isolation.
- The exact full-application 500,000-row release acceptance, final brand consistency and deployment remain planned engineering tasks.
