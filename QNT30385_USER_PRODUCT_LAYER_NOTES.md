# QNT30385 — User Product Layer

## Purpose
Convert Quantora from an internal operating system into a sellable customer-facing service layer.

## Included
- user registration
- service plan catalog
- portfolio configuration
- customer dashboard endpoint
- service request intake
- governance audit trail
- frontend user product panel
- smoke test

## Core endpoints
- GET /product/status
- GET /product/plans
- POST /product/user/register
- GET /product/users
- GET /product/user/{user_id}
- POST /product/portfolio/configure
- GET /product/portfolio/{user_id}
- POST /product/service/request
- GET /product/dashboard/{user_id}
- GET /product/audit

## Role in the system
This mission makes Quantora externally consumable.
It is the first productization layer where real clients can be onboarded, assigned plans, configured by risk profile, and mapped to a service-ready portfolio state.
