# QNT30379 — Adaptive Execution Policy Brain

## Mission
React to execution drift and market regime changes in real time, override routing logic dynamically, and protect capital when execution conditions deteriorate.

## Shipped
- `backend/adaptive_execution_policy_brain.py`
- `frontend/adaptive_execution_policy_panel.html`
- `backend/smoke_test_qnt30379.py`

## New endpoints
- `GET /adaptive-execution/status`
- `POST /adaptive-execution/rules/update`
- `POST /adaptive-execution/context`
- `POST /adaptive-execution/decide`
- `POST /adaptive-execution/dispatch`

## What it adds
- regime-aware execution policy decisions
- dynamic order size scaling
- volatility-aware participation limits
- execution tolerance overrides
- venue allow/block lists based on live quality
- direct dispatch into Venue Governor + Smart Order Router
- kill-switch style halt mode for extreme drift

## Validation
- compile checks passed
- smoke test passed
