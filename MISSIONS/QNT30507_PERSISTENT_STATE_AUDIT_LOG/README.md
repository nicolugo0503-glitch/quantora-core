QNT30507 — PERSISTENT STATE + AUDIT LOG

PURPOSE
Add restart-safe scheduler state persistence and an append-only audit trail so Quantora becomes operationally durable and accountable.

ADDS
- qnt30507_persistent_state_store.py
- qnt30507_persistent_scheduler_wrapper.py
- qnt30507_audit_router.py
- persistence_binding_example.py
- audit_contract.json
- frontend/mission_qnt30507_audit_log.html

ALSO CHANGES
- frontend/index.html (adds QNT30507 Audit button)
- frontend/conversation_missions_hub.html (adds QNT30507 card)

PRIMARY ENDPOINTS
- GET /api/audit/runtime-state
- GET /api/audit/logs

WHAT THIS UNLOCKS
- persisted runtime state
- restart recovery
- append-only audit trail
- operator accountability
- audit visibility in the frontend

STABILITY
Additive only. Minimal frontend button/card patch.
