QNT30617 — INVESTOR IDENTITY REGISTRY + MULTI-RECIPIENT DELIVERY PROFILES

ADDS
- backend/app/qnt30617_identity_registry_router.py
- frontend/mission_qnt30617_identity_registry.html
- backend/artifacts/investor_identity_registry/

UPGRADES
- identity registry summary
- create investor workflow
- create delivery profile workflow
- disable delivery profile workflow
- investor portal navigation into identity registry
- command center entry for QNT30617 Identity Registry

API
- GET /api/identity-registry
- POST /api/identity-registry/investor
- POST /api/identity-registry/profile
- POST /api/identity-registry/profile/disable
- GET /api/identity-registry/summary

PURPOSE
- create investor identity records and recipient-level delivery profiles
- support multi-recipient distribution configuration
- prepare Quantora for institutional delivery identity management
