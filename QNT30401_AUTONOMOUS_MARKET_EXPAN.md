# QNT30401 — Autonomous Market Expansion & Multi-Asset Routing Layer

## Purpose
Expand Quantora beyond a single market by enabling asset-class aware routing, market expansion decisions, venue selection, and routing history across equities, crypto, forex, futures, and options.

## Included
- supported asset-class state
- instrument universe intake
- asset-class aware routing
- venue and fallback selection
- market expansion decision endpoint
- route history
- audit trail
- frontend multi-asset routing panel
- smoke test

## Core endpoints
- GET /multi-asset-routing/status
- POST /multi-asset-routing/instruments/upsert
- GET /multi-asset-routing/instruments
- POST /multi-asset-routing/route
- POST /multi-asset-routing/expand
- GET /multi-asset-routing/routes
- GET /multi-asset-routing/expansion-history
- GET /multi-asset-routing/audit

## Role in the system
This mission gives Quantora the first real expansion layer for routing across multiple asset classes and venues instead of being constrained to a single-market path.
