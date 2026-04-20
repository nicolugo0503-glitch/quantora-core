# QNT30668 Integration Notes

Mission: Allocation Escalation Command

Integrated components:
- backend/app/qnt30668_allocation_escalation_command_router.py
- frontend/mission_qnt30668_allocation_escalation_command.html
- backend/app/main.py router wiring
- frontend/mission_registry.json mission registration
- QUANTORA_FULL_PROJECT_MANIFEST.json mission metadata refresh

Primary dependencies:
- QNT30667 Allocation Oversight Fabric
- QNT30663 Capital Committee Oversight Mesh
- QNT30664 Institutional Release Authority Grid
- QNT30652 Institutional Compliance Layer

New endpoints:
- GET /api/allocation-escalation-command/summary
- POST /api/allocation-escalation-command/run
- GET /api/allocation-escalation-command/audit
- POST /api/allocation-escalation-command/policy
