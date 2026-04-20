QNT30504 — TRUE LIVE END-TO-END STATE

PURPOSE
Move the control panel from fallback-capable behavior into true live mode by allowing fallback to be explicitly disabled on the frontend and rejected on the backend.

ADDS
- qnt30504_strict_live_adapter.py
- strict_live_binding_example.py
- strict_live_config.json

ALSO CHANGES
- frontend/qnt30501_live_system_client.js
- frontend/mission_qnt30493_real_control.html

WHAT THIS DOES
- adds a Strict live mode toggle to the control panel
- when strict live mode is enabled, missing backend state is shown as an error instead of silently using demo data
- adds a backend wrapper that rejects fallback-derived runtime, fund, investor, and exposure payloads

WHY THIS MATTERS
This is the transition from "safe demo if backend is absent" to "show me the real system or tell me it is not live."

STABILITY
Targeted frontend + additive backend wrapper patch only.
