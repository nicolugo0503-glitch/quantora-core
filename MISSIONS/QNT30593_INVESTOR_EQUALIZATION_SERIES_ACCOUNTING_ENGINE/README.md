QNT30593 — INVESTOR EQUALIZATION / SERIES ACCOUNTING ENGINE

ADDS
- backend/app/qnt30593_equalization_router.py
- frontend/mission_qnt30593_equalization.html
- backend/artifacts/investor_equalization_series/

UPGRADES
- equalization summary
- create series workflow
- close series workflow
- investor portal navigation into equalization
- command center entry for QNT30593 Equalization

API
- GET /api/equalization-series
- POST /api/equalization-series/create
- POST /api/equalization-series/close
- GET /api/equalization-series/summary

PURPOSE
- create investor series accounting and equalization tracking
- connect subscription capital to NAV-per-unit accounting
- prepare Quantora for allocator-grade series/equalization administration
