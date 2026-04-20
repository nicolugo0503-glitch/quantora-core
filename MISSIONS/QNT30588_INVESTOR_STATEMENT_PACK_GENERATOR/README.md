QNT30588 — INVESTOR STATEMENT PACK GENERATOR

ADDS
- backend/app/qnt30588_statement_pack_router.py
- frontend/mission_qnt30588_statement_pack.html
- backend/artifacts/investor_statement_packs/

UPGRADES
- statement pack summary
- generate pack workflow
- deliver pack workflow
- investor portal navigation into statement pack
- command center entry for QNT30588 Statement Pack

API
- GET /api/statement-packs
- POST /api/statement-packs/generate
- POST /api/statement-packs/deliver
- GET /api/statement-packs/summary

PURPOSE
- generate full investor reporting packages
- combine statement, pnl, and fee attribution into one pack
- prepare Quantora for investor-ready reporting delivery
