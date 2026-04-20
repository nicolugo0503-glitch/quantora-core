# QNT30384 — Autonomous Portfolio Manager

## Purpose
Convert Quantora performance intelligence into live capital orchestration.

## Included
- strategy snapshot ingestion
- portfolio rebalance engine
- dynamic capital allocation
- strategy kill logic based on drawdown thresholds
- allocation status reporting
- controls update endpoint
- governance audit trail
- frontend operator panel
- smoke test

## Core endpoints
- GET /portfolio-manager/status
- POST /portfolio-manager/controls/update
- POST /portfolio-manager/strategy/upsert
- POST /portfolio-manager/strategies/batch
- POST /portfolio-manager/rebalance
- GET /portfolio-manager/allocations
- GET /portfolio-manager/strategies
- GET /portfolio-manager/audit

## Integration path
QNT30383 performance outputs now feed directly into QNT30384 capital orchestration.

## Role in the system
This mission makes Quantora capable of continuously scaling winners, suppressing weak performers, and killing damaged strategies based on measurable portfolio evidence.
