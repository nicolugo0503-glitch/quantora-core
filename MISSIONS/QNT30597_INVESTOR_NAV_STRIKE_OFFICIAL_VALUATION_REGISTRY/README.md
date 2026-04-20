QNT30597 — INVESTOR NAV STRIKE + OFFICIAL VALUATION REGISTRY

ADDS
- backend/app/qnt30597_nav_strike_router.py
- frontend/mission_qnt30597_nav_strike.html
- backend/artifacts/investor_nav_strike_registry/

UPGRADES
- nav strike summary
- strike nav workflow
- finalize valuation workflow
- investor portal navigation into nav strike
- command center entry for QNT30597 NAV Strike

API
- GET /api/nav-strike
- POST /api/nav-strike/strike
- POST /api/nav-strike/finalize
- GET /api/nav-strike/summary

PURPOSE
- create an official valuation registry for investor NAV strikes
- bridge dealing day and rollforward state into official valuations
- prepare Quantora for institutional NAV strike administration
