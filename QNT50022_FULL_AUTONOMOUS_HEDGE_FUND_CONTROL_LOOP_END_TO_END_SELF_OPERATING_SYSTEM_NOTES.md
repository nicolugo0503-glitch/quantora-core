
# QNT50022 — Full Autonomous Hedge Fund Control Loop (End-to-End Self-Operating System)

Added:
- autonomous control loop engine
- state store + audit trail
- router + pydantic models
- frontend mission page
- mission registry + manifest updates

Integration posture:
- reads QNT50003 strategy deployment release queue
- blocks on QNT50004 risk kill-switch when policy requires
- reads QNT50005 performance posture
- delegates execution planning/execution to QNT50006
- enforces QNT50008 liquidity minimums
- can optionally gate on QNT50018 intercompany exceptions
