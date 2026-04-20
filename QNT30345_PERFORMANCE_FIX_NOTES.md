
# QNT30345 performance live-status fix

Fixed `/performance/live-status` crash caused by undefined `load_risk_lock_state`.
The endpoint now derives risk-lock state directly from `evaluate_risk_state(state)` and persists the updated state before returning.
