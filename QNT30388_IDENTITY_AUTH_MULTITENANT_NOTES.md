# QNT30388 — Identity, Auth, and Multi-Tenant Access Control

## Purpose
Add the core identity perimeter required for a real commercial Quantora deployment.

## Included
- tenant creation
- user creation with role binding
- password hashing scaffold
- login session issuance
- permission checks
- role updates
- invite issuance
- API key creation
- tenant dashboard
- governance audit trail
- frontend control panel
- smoke test

## Core endpoints
- GET /identity/status
- POST /identity/tenant/create
- GET /identity/tenants
- POST /identity/user/create
- GET /identity/users
- POST /identity/login
- POST /identity/access/check
- POST /identity/invite
- POST /identity/role/update
- POST /identity/api-key/create
- GET /identity/tenant/{tenant_id}/dashboard
- GET /identity/audit

## Role in the system
This mission creates the first real access boundary for Quantora.
Customers can now exist as isolated tenants, with role-based user access, session controls, and scoped API credentials.

## What this unlocks
- multi-client SaaS operation
- role-based portfolio and billing controls
- safer commercial onboarding
- future integration with payment, persistent DB, and production security layers
