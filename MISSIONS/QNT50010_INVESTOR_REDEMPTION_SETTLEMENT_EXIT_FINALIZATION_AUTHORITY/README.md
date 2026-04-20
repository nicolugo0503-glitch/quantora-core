# QNT50010 — Investor Redemption Settlement + Exit Finalization Authority

This mission closes the investor redemption lifecycle after treasury execution.

## Objectives
- bind executed treasury redemption transfers to institutionally governed exit cases
- inherit release authority issued under QNT50009
- require multi-party attestation before final close
- authorize and finalize investor exits with immutable audit lineage

## Core Endpoints
- `GET /investor-exit/summary`
- `POST /investor-exit/register-case`
- `POST /investor-exit/attest`
- `POST /investor-exit/authorize-finalization`
- `POST /investor-exit/finalize`
