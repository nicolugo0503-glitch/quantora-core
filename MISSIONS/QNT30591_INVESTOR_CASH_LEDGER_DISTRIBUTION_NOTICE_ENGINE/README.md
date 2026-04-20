QNT30591 — INVESTOR CASH LEDGER + DISTRIBUTION NOTICE ENGINE

ADDS
- backend/app/qnt30591_cash_ledger_router.py
- frontend/mission_qnt30591_cash_ledger.html
- backend/artifacts/investor_cash_ledger/

UPGRADES
- cash ledger summary
- distribution notice workflow
- process distribution workflow
- investor portal navigation into cash ledger
- command center entry for QNT30591 Cash Ledger

API
- GET /api/cash-ledger
- POST /api/cash-ledger/distribution-notice
- POST /api/cash-ledger/process
- GET /api/cash-ledger/summary

PURPOSE
- create an investor cash movement ledger
- track notices and processed distributions
- prepare Quantora for investor cash accounting and payout controls
