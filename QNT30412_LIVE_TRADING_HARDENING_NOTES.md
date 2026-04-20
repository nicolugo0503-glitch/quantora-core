
# QNT30412 — Live Trading Hardening

## Purpose
Harden the live trading path by enforcing guarded prechecks, kill-switch control, notional limits, position limits, and audited guarded execution.

## Included
- guarded config endpoint
- precheck endpoint
- guarded submit endpoint
- kill-switch endpoint
- execution log
- audit trail
- frontend hardening panel
- smoke test

## Core endpoints
- GET /live-hardening-v2/status
- POST /live-hardening-v2/config
- POST /live-hardening-v2/precheck
- POST /live-hardening-v2/submit
- POST /live-hardening-v2/kill-switch
- GET /live-hardening-v2/executions
- GET /live-hardening-v2/audit

## Role in the system
This mission tightens the bridge between broker execution and live safety controls so Quantora can move toward controlled real execution.
