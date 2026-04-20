# QNT30360 — Policy Simulator + Pre-Trade Approval Compiler

Mission objective: insert a governed pre-trade checkpoint between scenario output / autonomy intent and live execution.

## Delivered
- backend/policy_simulator.py
- backend/smoke_test_qnt30360.py
- frontend/policy_simulator_panel.html
- seeded backend/artifacts/policy_simulator.json through startup
- endpoints:
  - GET /policy-simulator/status
  - GET /policy-simulator/library
  - POST /policy-simulator/simulate
  - POST /policy-simulator/pretrade-compile

## Architecture impact
This mission adds a pre-trade compiler layer that turns execution intent into a governed approval artifact before live routing.

Core decisions covered:
- live notional escalation
- slippage threshold blocks
- rebalance-size escalation
- net exposure hard blocks
- delegated autonomy live escalation

## Validation
- python compileall executed successfully
- smoke test qnt30360 passed
