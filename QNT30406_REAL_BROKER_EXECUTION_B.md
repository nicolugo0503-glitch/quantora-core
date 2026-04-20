# QNT30406 — Real Broker Execution Bridge

## Purpose
Create the bridge between Quantora and a real broker connection flow so the platform can connect using environment credentials, submit orders, track fills, and maintain positions.

## Included
- broker env readiness detection
- broker connection endpoint
- order submit endpoint
- fill and position tracking
- order/fill/position views
- audit trail
- frontend live bridge panel
- smoke test

## Core endpoints
- GET /live-bridge/status
- POST /live-bridge/connect
- POST /live-bridge/order/submit
- GET /live-bridge/orders
- GET /live-bridge/fills
- GET /live-bridge/positions
- GET /live-bridge/audit

## Role in the system
This mission is the first direct bridge from Quantora into a live broker execution workflow. It should stay on paper mode until full live hardening is complete.
