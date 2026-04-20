QNT30585 — TRADE ATTRIBUTION BY INVESTOR SLEEVE

ADDS
- backend/app/qnt30585_trade_attribution_router.py
- frontend/mission_qnt30585_trade_attribution.html
- backend/artifacts/trade_attribution_by_sleeve/

UPGRADES
- trade attribution summary by sleeve
- record trade workflow
- investor portal navigation into trade attribution
- command center entry for QNT30585 Trade Attribution

API
- GET /api/trade-attribution
- POST /api/trade-attribution/trade
- GET /api/trade-attribution/summary

PURPOSE
- attribute executed trades to investor sleeves
- roll up notional and pnl by sleeve
- prepare Quantora for investor-level execution attribution
