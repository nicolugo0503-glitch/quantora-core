# QNT30707 — Recovery System

This mission adds a governed recovery layer on top of safety, forensic audit, fund administration, delivery, operator control, and release governance.

## Capabilities
- capture trusted state snapshots
- validate live state across audit, forensic, safety, and fund admin layers
- enter and clear safe mode
- execute soft, hard, and forensic recovery flows
- log recovery events into the immutable audit trail

## Core endpoints
- `GET /api/recovery-system/summary`
- `POST /api/recovery-system/capture-state`
- `POST /api/recovery-system/validate`
- `POST /api/recovery-system/recover`
- `POST /api/recovery-system/safe-mode`
- `POST /api/recovery-system/bootstrap-demo`
