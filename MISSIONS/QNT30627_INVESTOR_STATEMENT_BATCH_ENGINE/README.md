QNT30627 — INVESTOR STATEMENT BATCH ENGINE

ADDS
- backend/app/qnt30627_statement_batch_router.py
- frontend/mission_qnt30627_statement_batch.html
- backend/artifacts/investor_statement_batch_engine/

UPGRADES
- multi-investor batch statement generation by reporting period
- immutable period locking workflow
- reconciliation snapshot before official issuance
- statement registry with historical period storage
- investor-ready statement rendering with activity, allocations, waterfall, and equalization context
- demo bootstrap path for end-to-end institutional walkthroughs

API
- GET /api/investor-statements
- POST /api/investor-statements/bootstrap-demo
- POST /api/investor-statements/generate
- POST /api/investor-statements/lock
- GET /api/investor-statements/summary
- GET /api/investor-statements/period/{period}
- GET /api/investor-statements/statement/{period}/{investor_id}

PURPOSE
- close reporting periods at institutional scale
- generate official investor statements in batch
- preserve auditability through immutable locked periods
- connect investor identity, onboarding, capital ledger, waterfall, equalization, and pnl state into one reporting layer
