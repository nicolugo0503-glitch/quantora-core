# QNT50009 — Investor Cash Confirmation + Treasury Release Authority

This mission extends Quantora from treasury mobility into investor-directed cash release governance.

## Objectives
- register investor cash confirmation posture and bank-instruction status
- bind investor release requests to treasury transfer lineage
- capture dual acknowledgement before release
- authorize or block investor cash movement before QNT50008 execution

## Core Endpoints
- `GET /investor-cash-confirmation/summary`
- `POST /investor-cash-confirmation/register-investor`
- `POST /investor-cash-confirmation/request-release`
- `POST /investor-cash-confirmation/acknowledge`
- `POST /investor-cash-confirmation/authorize-release`
