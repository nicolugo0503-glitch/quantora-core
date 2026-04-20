# QNT30399 — Autonomous Multi-Strategy Competition & Selection Engine

## Purpose
Make strategies compete on measurable quality so Quantora can dynamically choose champions and allocate capital to the strongest candidates.

## Included
- strategy profile intake
- scoring engine
- competition run endpoint
- champion selection
- capital queue generation
- selection history
- audit trail
- frontend competition panel
- smoke test

## Core endpoints
- GET /strategy-competition/status
- POST /strategy-competition/strategies/upsert
- GET /strategy-competition/strategies
- POST /strategy-competition/run
- GET /strategy-competition/champion
- GET /strategy-competition/capital-queue
- GET /strategy-competition/history
- GET /strategy-competition/audit

## Role in the system
This mission enables Quantora to rank competing strategies and automatically choose which ones deserve capital in the current regime.
