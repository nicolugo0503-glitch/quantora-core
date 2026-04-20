# QNT30397 — Investor Reporting & Operator Intelligence Layer

## Purpose
Add investor-facing reporting and operator-facing intelligence briefs so Quantora can communicate performance, risk, execution posture, and capital state clearly.

## Included
- portfolio snapshot update
- strategy rankings update
- investor report generation
- operator brief generation
- alert surface
- audit trail
- frontend reporting/intelligence panel
- smoke test

## Core endpoints
- GET /reporting/status
- POST /reporting/portfolio/update
- GET /reporting/portfolio
- POST /reporting/strategies/update
- GET /reporting/strategies
- GET /reporting/alerts
- POST /reporting/investor-report/generate
- GET /reporting/investor-reports
- POST /reporting/operator-brief/generate
- GET /reporting/operator-briefs
- GET /reporting/audit

## Role in the system
This mission adds the communication layer needed for investor-grade visibility and operator-grade daily decision support.
