QNT30615 — REAL DISTRIBUTION CONSOLE + INVESTOR DELIVERY INBOX

ADDS
- backend/app/qnt30615_distribution_console_router.py
- frontend/mission_qnt30615_distribution_console.html
- backend/artifacts/investor_delivery_inbox/

UPGRADES
- distribution console summary
- sync inbox workflow
- open inbox item workflow
- star inbox item workflow
- archive inbox item workflow
- investor portal navigation into distribution console
- command center entry for QNT30615 Distribution Console

API
- GET /api/distribution-console
- POST /api/distribution-console/sync
- POST /api/distribution-console/open
- POST /api/distribution-console/star
- POST /api/distribution-console/archive
- GET /api/distribution-console/summary

PURPOSE
- create an investor delivery inbox on top of delivered reports
- make distribution operationally visible and usable
- prepare Quantora for investor-grade report consumption workflows
