QNT30624 — CAPITAL ALLOCATION ENGINE + LIVE INVESTOR CAPITAL LEDGER

ADDS
- backend/app/qnt30624_capital_ledger_router.py
- frontend/mission_qnt30624_capital_ledger.html
- backend/artifacts/investor_capital_ledger/

UPGRADES
- capital ledger summary
- create capital account workflow
- add ledger entry workflow
- capital allocation workflow
- ledger recalculation workflow
- investor portal navigation into capital ledger
- command center entry for QNT30624 Capital Ledger

API
- GET /api/capital-ledger
- POST /api/capital-ledger/account
- POST /api/capital-ledger/entry
- POST /api/capital-ledger/allocation
- POST /api/capital-ledger/recalculate
- GET /api/capital-ledger/summary

PURPOSE
- track committed, funded, unfunded capital and ownership
- maintain a live investor capital ledger
- prepare Quantora for fund-grade investor capital accounting
