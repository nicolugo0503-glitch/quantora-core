QNT30581 — FUND CLOSE LEDGER + INVESTOR ADMISSION STATE

ADDS
- backend/app/qnt30581_fund_close_router.py
- frontend/mission_qnt30581_fund_close_ledger.html
- backend/artifacts/fund_close_ledger/

UPGRADES
- fund close ledger summary
- create entry workflow
- admit entry workflow
- investor portal navigation into fund close ledger
- command center entry for QNT30581 Fund Close

API
- GET /api/fund-close
- POST /api/fund-close/create
- POST /api/fund-close/admit
- GET /api/fund-close/summary

PURPOSE
- create a structured fund close and investor admission ledger
- record admitted capital as investors move from commitment to formal admission
- prepare Quantora for fund close operations and allocator-grade tracking
