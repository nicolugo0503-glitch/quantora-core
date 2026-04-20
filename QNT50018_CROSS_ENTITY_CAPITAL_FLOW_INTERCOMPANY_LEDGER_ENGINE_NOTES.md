# QNT50018 — Cross-Entity Capital Flow + Intercompany Ledger Engine

This mission adds an institutional intercompany ledger layer to Quantora.

## What it does
- Registers cross-entity capital flows with optional legal-entity, fund, SPV, strategy, and jurisdiction fields.
- Syncs treasury mobility context from QNT50008, settlement posture from QNT50007, and supervisory evidence from QNT50015.
- Enforces approval gating for intercompany movement.
- Posts dual-entry affiliate journal records.
- Settles posted flows with treasury transfer lineage.

## Primary endpoints
- `GET /intercompany-ledger/health`
- `GET /intercompany-ledger/summary`
- `GET /intercompany-ledger/flows`
- `GET /intercompany-ledger/journal`
- `POST /intercompany-ledger/register-flow`
- `POST /intercompany-ledger/approve`
- `POST /intercompany-ledger/post`
- `POST /intercompany-ledger/settle`

## Integration notes
This layer is forward-compatible with future entity structure mapping work. In this ZIP, QNT50018 is integrated on top of the latest available real package in-session and does not assume QNT50016/QNT50017 code already exists in the artifact.
