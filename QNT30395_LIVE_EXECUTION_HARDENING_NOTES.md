# QNT30395 — Live Execution Hardening

## Purpose
Harden Quantora for future live trading by adding guardrails, position limits, daily notional limits, dual confirmation, and kill-switch controlled execution gating.

## Included
- live execution controls
- precheck endpoint
- guarded live trade request flow
- dual-approval confirmation flow
- guarded execution endpoint
- kill switch endpoint
- guardrail event log
- order and pending confirmation views
- frontend live hardening panel
- smoke test

## Core endpoints
- GET /live-hardening/status
- POST /live-hardening/controls/update
- POST /live-hardening/precheck
- POST /live-hardening/request
- POST /live-hardening/confirm
- POST /live-hardening/execute/{confirmation_id}
- POST /live-hardening/kill-switch
- GET /live-hardening/guardrails
- GET /live-hardening/orders
- GET /live-hardening/pending
- GET /live-hardening/audit

## Role in the system
This mission creates the mandatory safety perimeter before any real live capital deployment can be considered.
