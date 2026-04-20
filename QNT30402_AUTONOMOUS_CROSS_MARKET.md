# QNT30402 — Autonomous Cross-Market Portfolio Intelligence Engine

## Purpose
Build portfolio intelligence across multiple markets so Quantora can understand exposure concentration, cross-market signals, correlations, and rebalance needs at the portfolio level.

## Included
- market exposure updates
- correlation matrix updates
- cross-market signal ingestion
- portfolio intelligence recomputation
- rebalance recommendation generation
- rebalance suggestion view
- audit trail
- frontend cross-market intelligence panel
- smoke test

## Core endpoints
- GET /cross-market-intelligence/status
- POST /cross-market-intelligence/exposure/update
- GET /cross-market-intelligence/exposures
- POST /cross-market-intelligence/correlations/update
- GET /cross-market-intelligence/correlations
- POST /cross-market-intelligence/signal
- GET /cross-market-intelligence/signals
- POST /cross-market-intelligence/rebalance/recommend
- GET /cross-market-intelligence/rebalance-suggestions
- GET /cross-market-intelligence/audit

## Role in the system
This mission gives Quantora a portfolio-level brain across markets instead of isolated per-market views.
