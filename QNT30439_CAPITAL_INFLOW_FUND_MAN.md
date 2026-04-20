QNT30439 — Capital Inflow + Fund Management Layer

Adds:
- investor commitment intake
- fund treasury deposit / withdrawal tracking
- fund account creation
- fund summary endpoint
- institutional fund management panel

Endpoints:
- GET /workspace/fund/summary
- GET /workspace/fund/investors
- POST /workspace/fund/investors/add
- POST /workspace/fund/deposit
- POST /workspace/fund/withdraw
- GET /workspace/fund/cash-movements
- POST /workspace/fund/accounts/create
- GET /workspace/fund/accounts
