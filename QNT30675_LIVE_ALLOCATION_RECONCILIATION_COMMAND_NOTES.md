# QNT30675 Live Allocation Reconciliation Command

This layer reconciles live allocation outcomes after settlement across broker fills, capital ledger entries, PnL state, and governance artifacts.

## Scope
- Build a reconciliation book from live allocation sleeves.
- Score ledger alignment, fill capture, position matching, and documentation completion.
- Emit institutional actions: RECONCILE, REVIEW, HOLD, ESCALATE.
- Persist run audit trail and policy thresholds.

## API
- GET /api/live-allocation-reconciliation-command/summary
- POST /api/live-allocation-reconciliation-command/run
- GET /api/live-allocation-reconciliation-command/audit
- POST /api/live-allocation-reconciliation-command/policy
