QNT30517 — MULTI-FUND / MULTI-PORTFOLIO LAYER

PURPOSE
Add a scale layer so Quantora can manage multiple funds and multiple portfolios within those funds instead of operating as a single-fund system.

ADDS
- qnt30517_multi_fund_engine.py
- qnt30517_multi_fund_router.py
- multi_fund_binding_example.py
- multi_fund_contract.json
- frontend/mission_qnt30517_multi_fund.html

ALSO CHANGES
- frontend/index.html (adds QNT30517 Multi-Fund button)
- frontend/conversation_missions_hub.html (adds QNT30517 card)

PRIMARY ENDPOINTS
- POST /api/multifund/fund
- POST /api/multifund/portfolio
- POST /api/multifund/allocation
- GET /api/multifund/summary

WHAT THIS UNLOCKS
- multiple fund support
- multiple portfolio support
- fund-specific allocation targets
- deployable multi-fund operating view in the frontend

STABILITY
Additive only. Minimal frontend button/card patch.
