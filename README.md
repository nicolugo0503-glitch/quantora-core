# Quantora QNT30324C - Broker Capital Metrics Normalization

This package extends QNT30324B and repairs operator identity propagation across Quantora.

## What was fixed

- repaired legacy operator state migration by backfilling missing `operator_id`
- added session-derived operator context fallback using the logged-in email
- removed raw `operator_id` 500 crashes from strategy/workspace/snapshot flows
- added structured operator-context error classification
- preserved broker capital mode, risk engine, performance engine, governance, and Railway-safe startup

## Main endpoints

- `/health`
- `/version`
- `/auth/me`
- `/strategies/list`
- `/operator/workspace`
- `/command-center/snapshot`
- `/performance/metrics`
- `/risk-engine/status`
- `/admin/control-tower`

## Clean deploy behavior

This build ships without persisted artifacts. After deploy, register or log in again. If an old session survives without an operator id, the backend now repairs it automatically from the user record.

## Health checks

- Backend: `http://127.0.0.1:8010/health`
- Docs: `http://127.0.0.1:8010/docs`
- Frontend: `http://127.0.0.1:8010/`
- Version: `http://127.0.0.1:8010/version`
