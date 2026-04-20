QNT30566 — PAYMENT PROVIDER / EXTERNAL FUNDING RAILS

ADDS
- backend/app/qnt30566_payment_provider_router.py
- frontend/mission_qnt30566_payment_provider_center.html
- backend/artifacts/user_payment_provider/
- backend/artifacts/payment_webhooks/

UPGRADES
- payment provider connection profile
- external payment method attachment
- external deposit intent creation
- provider confirmation state
- webhook-ready deposit completion path into user ledger
- investor portal navigation into external rails
- command center entry for QNT30566 External Rails

API
- GET /api/user-payment-provider/status
- POST /api/user-payment-provider/connect
- POST /api/user-payment-provider/method
- POST /api/user-payment-provider/deposit-intent
- POST /api/user-payment-provider/confirm
- POST /api/payment-provider/webhook
- GET /api/payment-provider/webhooks

IMPORTANT
- this mission is provider-ready and webhook-ready
- it remains simulated until live provider credentials, endpoint secrets, and real provider callbacks are configured

PURPOSE
- create the abstraction layer required before true external funding integration
- prepare Quantora for Stripe/Dwolla-class funding flows without breaking the existing product path
