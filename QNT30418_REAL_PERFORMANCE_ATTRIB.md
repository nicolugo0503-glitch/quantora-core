# QNT30418 — Real Performance Attribution Engine

Institutional attribution layer merged into the canonical Quantora full project.

## Added
- `GET /performance/attribution`
- `GET /performance/strategies`
- `GET /performance/execution`
- `GET /performance/portfolio`
- `frontend/performance_attribution_panel.html`

## Attribution coverage
- trade-level attribution rows
- strategy-level attribution and promotion signal
- execution venue / mode quality summary
- portfolio contribution by symbol
- investor brief summary

## Billing hardening extension
QNT30417 was extended to QNT30417.1:
- real Stripe Checkout support when secrets and price IDs are present
- real Billing Portal support when secrets and price IDs are present
- signed Stripe webhook parsing
- billing metrics endpoints:
  - `GET /billing/metrics`
  - `GET /billing/mrr`
  - `GET /billing/churn`
  - `GET /billing/active-users`
- simulation fallback preserved when Stripe live env vars are absent

## Required live Stripe env
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_INSTITUTIONAL`
- `QUANTORA_APP_BASE_URL`
