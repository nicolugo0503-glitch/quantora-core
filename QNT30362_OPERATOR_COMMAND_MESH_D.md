# QNT30362 — Operator Command Mesh + Delegated Mandate Framework

## Mission
Build the operator command mesh that lets delegated operators issue scoped commands under institutional mandates, live gating, and controlled execution routing.

## Shipped
- `backend/operator_command_mesh.py`
- `frontend/operator_command_mesh_panel.html`
- `backend/smoke_test_qnt30362.py`

## New endpoints
- `GET /command-mesh/status`
- `POST /command-mesh/mandates/upsert`
- `POST /command-mesh/route`
- `POST /command-mesh/execute`

## What it adds
- delegated mandate registry
- operator-scoped live and paper permissions
- command routing with mandate checks
- live notional gating
- pending-to-executed promotion flow
- governance ledger events for command mesh actions

## Validation
- compile checks passed
- smoke test passed
