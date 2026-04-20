
# QNT30424 — Trade Lifecycle + Fill Engine

This mission adds the missing execution persistence loop on top of QNT30423.

## Added
- hybrid execution submit path (`broker_api` when broker credentials/base URL are present, otherwise simulated instant fills)
- persistent org-scoped orders, fills, positions, and lifecycle event tables
- lifecycle stages: `submitted`, `broker_routed`, `filled`
- position upsert logic with realized/unrealized PnL tracking
- frontend expansion for fills, positions, and lifecycle visibility

## New API
- `GET /workspace/execution/fills`
- `GET /workspace/positions`
- `GET /workspace/execution/lifecycle`

## Behavior
- paper/live broker profiles try real broker submission first
- if broker call fails or credentials are absent, Quantora falls back to simulated instant fills
- every execution creates an order row, fill row, lifecycle events, and position update
