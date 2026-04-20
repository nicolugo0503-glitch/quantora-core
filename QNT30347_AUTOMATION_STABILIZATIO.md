# QNT30347 — Automation Stabilization v2

## Mission
Harden Quantora's live automation loop so the AI Decision Layer + Capital Allocation System can operate continuously with production-grade resilience.

## What was added

### 1. Retry discipline inside the automation engine
- Added configurable retry policy per operator:
  - `retry_on_failure`
  - `max_retry_attempts`
  - `retry_backoff_seconds`
- Retries now occur before an operator cycle is marked failed.
- Retry scheduling is logged as first-class automation events.

### 2. Failure recovery controls
- Added operator recovery state reset:
  - clears paused / failure state
  - reschedules next run
  - can optionally force an immediate cycle
- Added worker recovery support when the loop thread is no longer healthy.

### 3. Cycle monitoring + telemetry
- Added worker heartbeat telemetry
- Added stall detection
- Added per-operator health status
- Added cycle duration tracking
- Added success / degraded / failure counters
- Added retry budget visibility in metrics output

### 4. Degraded-mode execution
- The automation cycle now treats non-core stages as recoverable:
  - broker reconciliation
  - monitoring / PnL sync
- If those fail, the cycle can still complete as `degraded` instead of crashing the entire loop.
- Core strategy execution remains critical and still fails hard when necessary.

## New API endpoints
- `GET /automation/health`
- `GET /automation/cycle-metrics`
- `POST /automation/recover`

## Updated endpoints
- `POST /automation/configure`
- `POST /automation/start`
- `GET /automation/worker-status`

These now expose stabilization controls and richer telemetry.

## Frontend
Updated `frontend/automation_loop_panel.html` into a stabilization control surface with:
- automation health snapshot
- cycle metrics
- retry configuration inputs
- operator recover action
- worker recover action

## Architectural effect
Quantora automation is no longer just an interval loop.
It is now a supervised execution service with:
- retry logic
- degraded-mode handling
- operator health state
- worker heartbeat monitoring
- explicit recovery controls

## Why this matters
This is the required bridge between:
- a working live system
- and a continuously operating institutional-grade autonomous system

Without this layer, the AI decision engine can make good decisions but still fail operationally.
With this layer, Quantora can withstand transient failure without surrendering control, risk discipline, or observability.
