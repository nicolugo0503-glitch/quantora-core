# QNT30449 — Institutional Reporting & LP Statement Engine

## Mission objective
Install the recurring institutional reporting surface for LP communication and fund reporting.

## Added backend capabilities
- NAV snapshot registry
- LP statement registry
- distribution registry
- reporting cycle registry
- reporting summary package and health score

## Added frontend capability
- institutional reporting and LP statement panel

## Key endpoints
- `GET /workspace/reporting/summary`
- `POST /workspace/reporting/nav/create`
- `POST /workspace/reporting/statements/create`
- `POST /workspace/reporting/distributions/create`
- `POST /workspace/reporting/cycles/create`

## Strategic value
This mission gives Quantora the recurring investor communication layer expected from real funds and allocators.
