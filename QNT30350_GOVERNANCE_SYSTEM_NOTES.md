# QNT30350 Governance System

## Mission
Governance System for institutional control, policy workflows, approval aging, and enforcement visibility.

## What shipped
- `backend/governance_system.py`
- new endpoints:
  - `GET /governance/status`
  - `POST /governance/policy/simulate`
  - `POST /governance/enforcement/evaluate`
  - `GET /governance/approvals/aging`
- updated governance defaults in `backend/app/main.py`
- new frontend panel:
  - `frontend/governance_system_panel.html`
- command center navigation updated
- new smoke test:
  - `backend/smoke_test_qnt30350.py`

## What it adds
- governance control-state and telemetry
- policy simulation before live capital/routing decisions
- enforcement snapshot across approvals, risk, and recent orders
- approval aging report for stale escalations
- expanded policy set for:
  - live order notional escalation
  - strategy rebalance oversight
  - slippage hold thresholds

## Validation
- Python compile check passed
- smoke test passed end-to-end

## Suggested next mission
Full autonomy control plane:
- approval delegation tiers
- governed autonomous execution states
- policy-based autonomous mode transitions
