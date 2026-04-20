
# QNT30354 — Real Venue Connectors + Unified Execution Bus

## Added
- `backend/real_venue_connectors.py`
- `backend/smoke_test_qnt30354.py`
- `frontend/real_venue_connectors_panel.html`

## New endpoints
- `GET /execution-bus/status`
- `POST /execution-bus/connectors/upsert`
- `POST /execution-bus/submit`
- `POST /execution-bus/ack`
- `POST /execution-bus/fill`

## Purpose
Move Quantora from venue/schema simulation toward a unified execution event bus with connector-backed routing, normalized submission, ack, fill, and reject telemetry.

## Architectural effect
- strategy intent stays abstract
- connector selection becomes explicit
- venue acknowledgements normalize into one lifecycle stream
- fill telemetry becomes comparable across venues
- active-order state moves into a bus-level registry instead of staying implicit per route
