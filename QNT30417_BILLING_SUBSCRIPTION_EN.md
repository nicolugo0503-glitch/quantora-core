# QNT30417 Billing + Subscription Enforcement

## Delivered
- Billing command layer with checkout session creation, portal session creation, webhook ingestion, audit, and subscription status endpoints.
- Runtime enforcement on execution routes for paper/live access based on plan and subscription state.
- Frontend billing panel at `frontend/billing.html`.
- `.env.example` for Stripe keys.
- Updated launchers to run the canonical FastAPI app.

## Key endpoints
- `GET /billing/plans`
- `GET /billing/subscription-status`
- `POST /billing/create-checkout-session`
- `POST /billing/portal-session`
- `POST /billing/webhook`
- `GET /billing/audit`

## Enforcement
- Paper execution requires an active/free subscription state.
- Live execution requires `institutional` plan plus active subscription.
