# QNT50010 — Investor Redemption Settlement + Exit Finalization Authority

This mission extends QNT50009 by moving from cash release approval into complete investor redemption closure governance.

## Delivered
- institutional exit-case registry bound to executed treasury transfers
- inherited release-authority lineage from QNT50009
- multi-party attestation workflow for ops, investor, reconciliation, and legal review
- exit finalization authority with expiry controls
- closed exit record generation with audit trail

## Core Endpoints
- `GET /investor-exit/summary`
- `POST /investor-exit/register-case`
- `POST /investor-exit/attest`
- `POST /investor-exit/authorize-finalization`
- `POST /investor-exit/finalize`
