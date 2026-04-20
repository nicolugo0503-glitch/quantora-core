QNT30570 — INSTITUTIONAL ADMIN CONSOLE + GLOBAL INVESTOR OVERSIGHT

ADDS
- backend/app/qnt30570_admin_console_router.py
- frontend/mission_qnt30570_admin_console.html
- backend/artifacts/institutional_admin_console/

UPGRADES
- global investor oversight summary
- aggregate balance and allocation monitoring
- global pending KYC and reconciliation warning visibility
- admin watchlist workflow
- admin notes workflow
- command center entry for QNT30570 Admin Console

API
- GET /api/admin-oversight/summary
- GET /api/admin-oversight/history
- POST /api/admin-oversight/watchlist
- POST /api/admin-oversight/note
- GET /api/admin-oversight/watchlist

PURPOSE
- create the institutional top-layer supervision surface
- allow global monitoring across all onboarded investors
- prepare Quantora for allocator-grade operations oversight
