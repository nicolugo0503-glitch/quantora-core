QNT30557 — MULTI-USER SYSTEM

ADDS
- backend/app/qnt30557_multi_user_router.py
- frontend/login.html
- frontend/investor_portal.html
- frontend/mission_qnt30557_multi_user_center.html
- backend/artifacts/user_ledgers/
- backend/artifacts/user_performance/

UPGRADES
- onboarding now uses backend registration
- deposit now writes to user-isolated capital ledger
- sign in uses backend session auth
- investor portal reads user-specific capital and performance

API
- POST /api/user/register
- POST /api/user/login
- POST /api/user/logout
- GET /api/user/me
- GET /api/user-capital
- POST /api/user-capital/deposit
- POST /api/user-capital/withdraw
- GET /api/user-performance

PURPOSE
- isolate capital and performance per user
- move product entry from shared demo state toward a real multi-user platform
