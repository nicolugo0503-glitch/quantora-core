QNT30586 — INVESTOR PNL LEDGER + REALIZED/UNREALIZED ATTRIBUTION

ADDS
- backend/app/qnt30586_pnl_ledger_router.py
- frontend/mission_qnt30586_pnl_ledger.html
- backend/artifacts/investor_pnl_ledger/

UPGRADES
- pnl ledger summary by sleeve
- mark position workflow
- realize pnl workflow
- investor portal navigation into pnl ledger
- command center entry for QNT30586 PnL Ledger

API
- GET /api/pnl-ledger
- POST /api/pnl-ledger/mark
- POST /api/pnl-ledger/realize
- GET /api/pnl-ledger/summary

PURPOSE
- attribute realized and unrealized pnl at investor sleeve level
- create investor-level pnl accounting from execution data
- prepare Quantora for full sleeve-level performance attribution
