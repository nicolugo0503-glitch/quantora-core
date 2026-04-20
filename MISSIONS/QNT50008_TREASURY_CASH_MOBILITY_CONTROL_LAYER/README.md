# QNT50008 — Treasury + Cash Mobility Control Layer

This mission extends Quantora from settlement correctness into treasury governance.

## Objectives
- synchronize treasury liquidity with QNT50007 settlement state
- maintain reserve and operating cash protection before cash moves
- stage, approve, and execute treasury transfers with audit-grade lineage
- rebalance internal treasury accounts to policy targets

## Core Endpoints
- `GET /treasury/summary`
- `POST /treasury/sync-settlement`
- `POST /treasury/stage-transfer`
- `POST /treasury/approve-transfer`
- `POST /treasury/execute-transfer`
- `POST /treasury/rebalance`
