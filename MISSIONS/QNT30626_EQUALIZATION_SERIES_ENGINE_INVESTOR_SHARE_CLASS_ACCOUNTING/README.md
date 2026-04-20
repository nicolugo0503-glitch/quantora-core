QNT30626 — EQUALIZATION SERIES ENGINE + INVESTOR SHARE-CLASS ACCOUNTING

ADDS
- backend/app/qnt30626_equalization_router.py
- frontend/mission_qnt30626_equalization.html
- backend/artifacts/equalization_series_engine/

UPGRADES
- equalization summary
- share class creation workflow
- series account creation workflow
- equalization event posting workflow
- share class revaluation workflow
- investor portal navigation into equalization engine
- command center entry for QNT30626 Equalization Engine

API
- GET /api/equalization
- POST /api/equalization/share-class
- POST /api/equalization/series
- POST /api/equalization/event
- POST /api/equalization/revalue
- GET /api/equalization/summary

PURPOSE
- manage investor share classes and series accounting
- track equalization credits and revaluation across series
- prepare Quantora for hedge-fund-grade share-class accounting
