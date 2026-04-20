# QNT30428 — Position Exit + Reduce Engine

Built on top of the working QNT30427 full merged branch.

## Added
- `POST /workspace/positions/reduce`
- `POST /workspace/positions/close`
- `POST /workspace/positions/flatten`
- integrated position action buttons in `frontend/org_execution_capital_engine.html`

## Behavior
- reduce/close/flatten create a new execution order row first
- route through the existing hybrid broker path
- persist fills
- update the existing org position row
- emit lifecycle events:
  - `reduce_requested`
  - `reduce_submitted`
  - `close_requested`
  - `close_submitted`
  - `flatten_requested`
  - `flatten_submitted`
  - `position_reduced`
  - `position_closed`

## Operator controls
- Reduce 25%
- Reduce 50%
- Close
- Flatten All

## Validation
- backend compile check passed
- `backend/smoke_test_qnt30428.py` passed
