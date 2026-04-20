QNT30567 — LIVE PROVIDER ACTIVATION

ADDS
- backend/app/qnt30567_live_provider_activation_router.py
- frontend/mission_qnt30567_live_provider_activation_center.html
- backend/artifacts/payment_provider_activation/

UPGRADES
- provider selection for Stripe or Dwolla
- env readiness checks
- webhook readiness checks
- customer/method readiness checks
- live-vs-simulated provider activation status
- investor portal navigation into provider activation
- command center entry for QNT30567 Provider Activation

API
- GET /api/payment-provider-activation/status
- POST /api/payment-provider-activation/select
- POST /api/payment-provider-activation/check
- GET /api/payment-provider-activation/env
- POST /api/payment-provider-activation/mock-live

IMPORTANT
- this mission does not embed real provider credentials
- true live activation requires env vars and webhook secrets to be configured in deployment

PURPOSE
- bridge simulated provider abstraction into deployment-ready live provider activation
- make readiness visible before turning on real external funding rails
