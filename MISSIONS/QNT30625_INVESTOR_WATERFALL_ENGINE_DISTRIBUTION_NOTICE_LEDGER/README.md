QNT30625 — INVESTOR WATERFALL ENGINE + DISTRIBUTION NOTICE LEDGER

ADDS
- backend/app/qnt30625_waterfall_router.py
- frontend/mission_qnt30625_waterfall.html
- backend/artifacts/investor_waterfall_engine/

UPGRADES
- waterfall summary
- run waterfall workflow
- distribution notice publishing workflow
- investor portal navigation into waterfall engine
- command center entry for QNT30625 Waterfall Engine

API
- GET /api/waterfall
- POST /api/waterfall/run
- POST /api/waterfall/notice/publish
- GET /api/waterfall/summary

PURPOSE
- calculate hurdle, carry, and LP distribution pools
- generate investor distribution notices
- prepare Quantora for fund-grade waterfall and payout workflows
