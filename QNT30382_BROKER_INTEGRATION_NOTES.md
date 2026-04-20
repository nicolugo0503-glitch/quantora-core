# QNT30382 — Broker Integration Layer

## Purpose
Connect Quantora's autonomous execution stack to broker adapters with paper-mode defaults.

## Included
- Alpaca paper adapter scaffold
- Binance paper adapter scaffold
- IBKR paper adapter scaffold
- order validation
- paper order submission
- batch dispatch
- kill switch
- audit log
- frontend operations panel
- smoke test

## Core endpoints
- GET /broker-integration/status
- POST /broker-integration/credentials/{broker}
- POST /broker-integration/controls/kill-switch?enabled=true|false
- POST /broker-integration/order/validate
- POST /broker-integration/order/submit
- POST /broker-integration/dispatch
- GET /broker-integration/audit

## Integration path
QNT30379 -> QNT30380 -> QNT30381 -> QNT30382
