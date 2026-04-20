QNT30602 — IMMUTABLE AUDIT TRAIL + CONTROL EVIDENCE REGISTRY

ADDS
- backend/app/qnt30602_audit_trail_router.py
- frontend/mission_qnt30602_audit_trail.html
- backend/artifacts/immutable_audit_trail/

UPGRADES
- audit trail summary
- capture reconciliation state workflow
- capture exception state workflow
- add control evidence workflow
- investor portal navigation into audit trail
- command center entry for QNT30602 Audit Trail

API
- GET /api/audit-trail
- POST /api/audit-trail/capture-reconciliation
- POST /api/audit-trail/capture-exception-state
- POST /api/audit-trail/evidence
- GET /api/audit-trail/summary

PURPOSE
- create immutable chained audit records
- preserve control evidence and state snapshots
- prepare Quantora for audit-grade evidence retention and integrity validation
