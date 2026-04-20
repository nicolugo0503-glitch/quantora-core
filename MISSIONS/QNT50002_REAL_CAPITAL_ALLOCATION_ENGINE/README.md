# QNT50002 — Real Capital Allocation Engine

This mission adds an institutional capital allocation layer that:
- scores eligible strategies
- preserves reserve capital under stress
- produces approval-ready allocation plans
- exports execution handoff tickets for the broker execution layer

Primary runtime files live in:
- `backend/app/allocation/engine.py`
- `backend/app/qnt50002_real_capital_allocation_engine_router.py`
- `backend/app/state/allocation_state.json`
