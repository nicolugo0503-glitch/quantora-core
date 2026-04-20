# QNT30415 — Full System Wiring (Real Platform Mode)

## Purpose
Wire auth, accounts, runtime, and trade recording into one connected system so the logged-in user becomes the active operator and account capital/PnL drive the dashboard state.

## Included
- persistent register/login
- session binding into runtime
- user account lookup
- trade recording tied to a user
- runtime status driven by active session
- audit trail
- frontend system wiring panel

## Core endpoints
- POST /platform/register
- POST /platform/login
- POST /platform/session/bind
- GET /platform/runtime/status
- GET /platform/account/{user_id}
- POST /platform/trade/record
- GET /platform/trades/{user_id}
- GET /platform/audit

## Role in the system
This mission turns Quantora from isolated modules into a connected platform flow where auth, accounts, capital, and runtime state are unified.
