# QNT30352 — Broker Abstraction + Multi-Market Expansion

## Mission Outcome
Quantora now has a dedicated broker abstraction layer that separates market routing decisions from strategy logic and opens controlled expansion paths beyond single-broker equities execution.

## What was added
- `backend/broker_abstraction.py`
- `GET /broker-abstraction/status`
- `POST /broker-abstraction/router/evaluate`
- `POST /broker-abstraction/brokers/upsert`
- `POST /broker-abstraction/markets/upsert`
- `POST /broker-abstraction/portfolio/expand`
- `frontend/broker_abstraction_panel.html`
- `backend/smoke_test_qnt30352.py`
- startup seeding for `backend/artifacts/broker_abstraction.json`

## Architectural impact
This moves Quantora from direct broker-specific thinking toward an execution fabric:
- strategy layer can target a market instead of a hard-coded venue
- broker capability metadata is now explicit
- route selection considers fee, latency, reliability, slippage penalty, urgency, and execution mode
- cross-market portfolio expansion is stateful and governed

## Default expansion footprint
- equities
- crypto
- futures
- forex

## Broker footprint
- alpaca as live/paper primary for supported lanes
- simulation brokers for crypto, futures, and forex expansion
- extensible upsert flow for future real broker adapters

## Validation
- python compile check
- qnt30352 smoke test
- openapi route presence confirmed

## Next mission
Broker adapter hardening and venue-specific execution connectors:
- adapter interface per venue
- symbol normalization across markets
- venue-specific order schemas
- market data abstraction
- broker failover / route degradation handling
