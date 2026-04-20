# QNT50023 — Executive AI Capital Committee + Decision Memory Layer

## Objective
Add an executive governance layer that can remember prior capital decisions, evaluate new committee proposals, and issue approval-grade directives without breaking the existing Quantora package structure.

## Core additions
- Executive decision memory registry with confidence and outcome-quality scoring
- Capital committee proposal workflow
- Committee approval / defer / reject decision records
- QNT50022 control-loop context sync
- Audit log for institutional traceability

## Integration
QNT50023 consumes posture from:
- QNT50004 risk kill-switch
- QNT50005 performance engine
- QNT50008 treasury cash mobility
- QNT50018 intercompany ledger
- QNT50022 autonomous control loop

## Primary endpoints
- GET `/executive-committee/health`
- GET `/executive-committee/summary`
- POST `/executive-committee/sync-context`
- POST `/executive-committee/record-memory`
- POST `/executive-committee/propose`
- POST `/executive-committee/approve`
- POST `/executive-committee/reset`
