# QNT30721 — Executive Scenario Arbitration Layer

Institutional scenario-arbitration layer that resolves conflicting executive, strategy, liquidity, regime, defense, and committee inputs into one governed capital decision.

## Added
- backend/app/qnt30721_executive_scenario_arbitration_layer_router.py
- frontend/mission_qnt30721_executive_scenario_arbitration_layer.html
- backend/test_qnt30721_smoke.py

## Core endpoints
- GET /api/executive-scenario-arbitration-layer/summary
- POST /api/executive-scenario-arbitration-layer/build-scenarios
- POST /api/executive-scenario-arbitration-layer/detect-conflicts
- POST /api/executive-scenario-arbitration-layer/arbitrate
- GET /api/executive-scenario-arbitration-layer/decision
- POST /api/executive-scenario-arbitration-layer/policy
- POST /api/executive-scenario-arbitration-layer/bootstrap-demo

## Behavior
- builds competing scenarios
- detects conflicts across actions, confidence, regime, liquidity, and defense posture
- arbitrates a governed winner with blockers and review gating
- records arbitration-book entries and alerts
