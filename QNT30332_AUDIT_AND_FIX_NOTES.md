# QNT30332 Audit and Fix Notes

## What was audited
- `frontend/index.html`
- `backend/app/main.py`
- capital-source flow
- operator capital flow
- broker-capital risk behavior

## Root causes found
1. `frontend/index.html` had a corrupted JavaScript block with repeated injected function bodies.
   - Multiple functions were cut off before completion.
   - The same routing/execution helper functions were duplicated many times inside unrelated handlers.
   - This broke button wiring for actions such as:
     - Set My Capital
     - Set Capital Source
     - Run All Running Strategies Once
     - Connect / Disconnect Alpaca
     - several admin and control actions

2. Capital source mode handling was strict on the backend.
   - The backend expected only `internal` or `broker`.
   - This is correct architecturally, but operator-facing UX benefits from accepting `alpaca` as an alias and normalizing it to `broker`.

3. Risk evaluation could show a false drawdown breach when broker capital mode was selected while broker capital was unavailable.
   - Example: switching from funded internal mode to unavailable broker mode could produce a `100%` drawdown and mark the system as breached.
   - This is misleading; the correct state is `UNKNOWN` until broker capital is available.

## Fixes applied
### Frontend
- Replaced the broken script block in `frontend/index.html` with a clean implementation.
- Rewired all visible dashboard actions to the correct backend endpoints.
- Preserved the existing UI layout and element IDs so the page remains operational.
- Added clean refresh behavior for:
  - auth/session
  - workspace/capital
  - strategy registry and logs
  - Alpaca broker status
  - manual orders
  - risk engine
  - governance / approvals
  - multi-operator panels
  - AI activation panels
  - ledger / snapshot
  - broker routing
  - execution engine
  - strategy signals

### Backend
- Normalized capital-source update so `alpaca` is accepted as a user-friendly alias for `broker`.
- Fixed risk evaluation so invalid/unavailable broker capital produces `UNKNOWN` instead of a false drawdown breach.

## What this should fix for you
- `Set My Capital` now correctly calls `/allocator/operator-capital/set`.
- `Set Capital Source` now correctly calls `/capital-source/update`.
- Workspace pills and capital metrics should refresh after those actions.
- Broker-capital mode should no longer create a fake drawdown breach when broker capital is unavailable.

## Recommended test sequence after unzip
1. Login as admin.
2. Connect Alpaca paper mode.
3. Click `Set My Capital` with a small number like `1000`.
4. Click `Set Capital Source` and switch to:
   - `internal` to verify allocated capital shows up
   - `alpaca broker capital` to verify broker equity / buying power show up
5. Place one paper order.
6. Confirm:
   - broker status panel updates
   - workspace capital pills update
   - order appears in orders table
   - no `CAPITAL_GUARD` error when capital is actually available

## Known limitation
- This fix targets the audited QNT30332 package specifically.
- Later missions should merge this repaired frontend and backend behavior forward so the newer builds inherit the same fixes.
