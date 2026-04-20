# QNT50028 — Institutional Reauthorization + Post-Recovery Capital Reinstatement Layer

This mission adds a governed post-recovery capital reinstatement surface that restores capital only after recovery evidence, risk clearance, and institutional reauthorization.

## Added
- Reauthorization case registry with remediation action and recovery cycle lineage
- Reinstatement approval gate with treasury-capacity and risk-clearance checks
- Executed reinstatement event ledger with destination account and capital restored
- Context sync against remediation recovery, breach resolution, risk, and treasury layers

## Primary backend endpoints
- `GET /capital-reauthorization/health`
- `GET /capital-reauthorization/summary`
- `GET /capital-reauthorization/reauthorizations`
- `GET /capital-reauthorization/reinstatements`
- `POST /capital-reauthorization/configure`
- `POST /capital-reauthorization/sync-context`
- `POST /capital-reauthorization/register-reauthorization`
- `POST /capital-reauthorization/approve-reinstatement`
- `POST /capital-reauthorization/execute-reinstatement`
- `POST /capital-reauthorization/close-reauthorization`
- `POST /capital-reauthorization/reset`
