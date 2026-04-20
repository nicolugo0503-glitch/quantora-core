# QNT50004 — Risk Kill-Switch System

Quantora now includes a mandatory risk stop layer between deployment intent and broker execution.

## What was added
- Dedicated `risk_control` package with persisted state and enforcement engine
- Router with health, configuration, metrics, trigger, reset, and override endpoints
- Pre-trade integration inside `backend/app/execution/order_router.py`
- Safe-mode synchronization across execution, allocation, and strategy deployment states
- Frontend mission page, mission registry entry, mission directory, and smoke test

## Enforcement model
Critical breaches force:
- `execution.mode = paper`
- `execution.safe_mode = true`
- `execution.active_broker = paper`

This mission was added into the same reference package structure and only extended the system with QNT50004 files.
