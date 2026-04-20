# QNT30403 — Autonomous Global Risk Mesh & Capital Defense System

## Purpose
Create a global risk mesh that aggregates multiple risk nodes and automatically triggers capital defense behavior such as alerts, throttling, and freeze conditions.

## Included
- risk node updates
- batch risk node updates
- global risk score computation
- defense policy updates
- automatic capital defense evaluation
- defense action history
- mesh event log
- frontend risk mesh panel
- smoke test

## Core endpoints
- GET /global-risk-mesh/status
- POST /global-risk-mesh/node/update
- POST /global-risk-mesh/nodes/update
- GET /global-risk-mesh/nodes
- POST /global-risk-mesh/policies/update
- POST /global-risk-mesh/defense/evaluate
- GET /global-risk-mesh/defense-actions
- GET /global-risk-mesh/events
- GET /global-risk-mesh/audit

## Role in the system
This mission gives Quantora a system-wide capital defense layer that can react to aggregate risk instead of isolated subsystem warnings.
