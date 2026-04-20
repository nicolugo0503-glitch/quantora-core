QNT30578 — SUBSCRIPTION DOCUMENTS + E-SIGNATURE WORKFLOW

ADDS
- backend/app/qnt30578_subscription_esign_router.py
- frontend/mission_qnt30578_subscription_esign.html
- backend/artifacts/subscription_documents_esign/

UPGRADES
- subscription document summary
- send document workflow
- sign document workflow
- review workflow
- investor portal navigation into subscription docs
- command center entry for QNT30578 Subscription Docs

API
- GET /api/subscription-docs
- POST /api/subscription-docs/send
- POST /api/subscription-docs/sign
- POST /api/subscription-docs/review
- GET /api/subscription-docs/summary

PURPOSE
- create the investor subscription packet and e-signature layer
- support capital onboarding through subscription agreements and acknowledgements
- prepare Quantora for operational subscription workflows
