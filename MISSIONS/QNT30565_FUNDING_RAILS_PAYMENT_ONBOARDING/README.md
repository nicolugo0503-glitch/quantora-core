QNT30565 — FUNDING RAILS / PAYMENT ONBOARDING

ADDS
- backend/app/qnt30565_funding_router.py
- frontend/mission_qnt30565_funding_center.html
- backend/artifacts/user_funding_profiles/
- backend/artifacts/user_payment_intents/

UPGRADES
- user-scoped funding profile
- KYC lifecycle state (simulated)
- payment method storage (simulated)
- deposit intent creation and controlled confirmation into user ledger
- investor portal navigation into funding rails
- command center entry for QNT30565 Funding Rails

API
- GET /api/user-funding/profile
- POST /api/user-funding/method
- POST /api/user-funding/kyc/start
- POST /api/user-funding/kyc/approve
- GET /api/user-funding/intents
- POST /api/user-funding/deposit-intent
- POST /api/user-funding/deposit-confirm
- GET /api/user-funding/summary

PURPOSE
- bridge product onboarding into funding operations
- prepare Quantora for real-world capital onboarding workflows
- create the final simulated funding layer before real payment integrations
