# QNT30430 — Operator Approval + Governance Workflow

Adds:
- pending approval queue
- approval history ledger
- submit/approve/reject governance actions
- governance UI embedded in org execution panel
- lifecycle events for approval_submitted / approval_approved / approval_rejected

New endpoints:
- GET /workspace/governance/pending
- GET /workspace/governance/history
- POST /workspace/governance/submit
- POST /workspace/governance/approve
- POST /workspace/governance/reject
