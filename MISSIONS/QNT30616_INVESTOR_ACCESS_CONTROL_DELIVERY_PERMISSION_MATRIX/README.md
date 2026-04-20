QNT30616 — INVESTOR ACCESS CONTROL + DELIVERY PERMISSION MATRIX

ADDS
- backend/app/qnt30616_access_control_router.py
- frontend/mission_qnt30616_access_control.html
- backend/artifacts/investor_access_control/

UPGRADES
- access control summary
- configure permission matrix workflow
- capability check workflow
- inbox filtering workflow
- investor portal navigation into access control
- command center entry for QNT30616 Access Control

API
- GET /api/access-control
- POST /api/access-control/configure
- POST /api/access-control/check
- POST /api/access-control/filter-inbox
- GET /api/access-control/summary

PURPOSE
- apply delivery permissions across investor-facing distribution surfaces
- create a permission matrix for report access and inbox visibility
- prepare Quantora for controlled investor access governance
