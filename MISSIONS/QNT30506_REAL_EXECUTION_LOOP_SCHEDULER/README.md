QNT30506 — REAL EXECUTION LOOP + SCHEDULER

PURPOSE
Add the continuous execution heartbeat for Quantora so the system can run cycles on an interval instead of only responding to manual UI refreshes.

ADDS
- qnt30506_execution_loop_scheduler.py
- qnt30506_scheduler_router.py
- scheduler_binding_example.py
- scheduler_contract.json
- frontend/mission_qnt30506_execution_loop.html

ALSO CHANGES
- frontend/index.html (adds QNT30506 Scheduler button)
- frontend/conversation_missions_hub.html (adds QNT30506 card)

PRIMARY ENDPOINTS
- GET /api/runtime/loop-state
- POST /api/runtime/loop-control

CONTROL ACTIONS
- start
- pause
- resume
- kill
- set_interval

WHAT THIS UNLOCKS
- continuously running execution loop
- scheduler state visible in the frontend
- logs and last-result visibility
- a real heartbeat layer for Quantora

STABILITY
Additive only. Minimal frontend button/card patch.
