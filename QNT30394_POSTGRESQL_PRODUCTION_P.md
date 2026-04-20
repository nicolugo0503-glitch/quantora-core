# QNT30394 — PostgreSQL Production Persistence

## Purpose
Add a PostgreSQL-shaped production persistence layer for environment readiness, migrations, table persistence, and audit visibility.

## Included
- postgres env readiness endpoint
- migration application endpoint
- tenant persistence
- user persistence
- strategy persistence
- order persistence
- table inspection endpoint
- audit trail
- frontend postgres panel
- smoke test

## Core endpoints
- GET /postgres/status
- POST /postgres/env/update
- POST /postgres/migrations/apply
- POST /postgres/tenants/create
- POST /postgres/users/create
- POST /postgres/strategies/create
- POST /postgres/orders/create
- GET /postgres/table/{table_name}
- GET /postgres/audit

## Role in the system
This mission prepares Quantora for production-grade relational persistence by introducing a PostgreSQL-oriented operational layer before full live database integration.
