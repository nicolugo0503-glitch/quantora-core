# QNT30443 — Real Fund Mode

## Added
- Organization-scoped fund pools table and default treasury pool bootstrap
- Investor registry with commitment and equity tracking
- Capital flow ledger for deposits, withdrawals, subscriptions, and pool seed events
- Fund-level summary package with NAV, inflows/outflows, pool utilization, and strategy allocation view
- Real Fund Mode frontend panel

## Endpoints
- `GET /workspace/fund-mode/summary`
- `GET /workspace/fund-mode/pools`
- `GET /workspace/fund-mode/investors`
- `GET /workspace/fund-mode/flows`
- `POST /workspace/fund-mode/pools/create`
- `POST /workspace/fund-mode/investors/add`
- `POST /workspace/fund-mode/flows/deposit`
- `POST /workspace/fund-mode/flows/withdraw`

## Operating model
- Default pool is created automatically from the first organization account if none exists.
- Pool allocated and reserve balances sync from organization capital allocations.
- Investor commitments can fund the default treasury pool immediately.
- Manual control remains intact; this mission adds fund accounting, not autonomous money movement.
