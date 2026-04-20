# QNT30422 — Multi-Tenant Institutional Workspace Layer

This mission adds the first canonical organization/workspace layer to Quantora.

## Added
- SQLite-backed `organizations`, `workspace_memberships`, and `organization_accounts` tables
- automatic default workspace seeding for the authenticated operator
- active workspace switching persisted in session state
- role-capability model: owner, admin, trader, analyst, observer
- org-scoped treasury summary and member listing
- frontend panel: `frontend/workspace_institutional_layer.html`

## API
- `GET /workspace/roles`
- `GET /workspace/organizations`
- `GET /workspace/context`
- `POST /workspace/organizations/create`
- `POST /workspace/members/add`
- `POST /workspace/switch`
- `GET /workspace/accounts`

## Current scope
This build establishes canonical multi-tenant structure and org-level context. It does not yet fully enforce workspace isolation across every historical module; that should be the next hardening pass.
