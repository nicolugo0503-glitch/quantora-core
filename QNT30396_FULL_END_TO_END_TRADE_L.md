# QNT30396 — Full End-to-End Trade Lifecycle Integration

## Purpose
Integrate the full path from trade idea to allocation, execution request, order submission, fill reporting, position update, and performance recording.

## Included
- trade idea intake
- allocation decision intake
- execution request stage
- order submission stage
- fill reporting
- position updates
- performance record generation
- lifecycle event timeline
- demo run endpoint
- frontend lifecycle panel
- smoke test

## Core endpoints
- GET /trade-lifecycle/status
- POST /trade-lifecycle/idea
- POST /trade-lifecycle/allocation
- POST /trade-lifecycle/execution-request
- POST /trade-lifecycle/order-submit/{trade_id}
- POST /trade-lifecycle/fill
- GET /trade-lifecycle/trade/{trade_id}
- GET /trade-lifecycle/positions
- GET /trade-lifecycle/lifecycle
- POST /trade-lifecycle/run-demo
- GET /trade-lifecycle/audit

## Role in the system
This mission ties Quantora's core systems into one traceable trade lifecycle so decisions, capital, execution, positions, and performance are no longer isolated modules.
