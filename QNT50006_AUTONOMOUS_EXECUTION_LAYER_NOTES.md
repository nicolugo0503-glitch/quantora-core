# QNT50006 — Autonomous Execution Layer

Quantora now includes a controlled autonomous execution fabric that turns approved deployment tickets into broker-submittable orders without breaking safe mode, risk governance, or audit lineage.

## What was added
- Dedicated `autonomous_execution` package with state store and execution engine
- Router with health, policy, queue, cycles, ingest, planning, execution, and reset endpoints
- Cross-mission gating against QNT50004 risk state and QNT50005 performance metrics
- Release queue ingestion from QNT50003 and execution routing through QNT50001
- Frontend mission page, mission directory, mission registry entry, manifest update, and smoke test

## Institutional behavior delivered
- Policy-gated autonomy with explicit enablement requirement
- Live-mode blocking when safe mode is active or broker posture is invalid
- Target-capital to order-quantity conversion with market price controls
- Manual escalation path for reduction tickets that require position inventory context
- Cycle-level audit traceability and execution history linkage

This mission was added into the same reference package structure and only extended the system with QNT50006 files.
