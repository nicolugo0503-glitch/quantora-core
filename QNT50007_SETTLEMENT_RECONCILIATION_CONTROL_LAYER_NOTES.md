# QNT50007 — Settlement + Reconciliation Control Layer

Quantora now contains an institutional post-trade control layer that closes the loop after execution.

## What was added
- Dedicated `settlement_reconciliation` package with state store and engine
- Router with health, state, summary, pending, ledger, break, ingest, confirm, reconcile, configure, and reset endpoints
- Settlement ticket generation from QNT50001 execution fills and QNT50006 autonomous execution output
- Cash ledger and position ledger booking once settlement is confirmed
- Broker snapshot reconciliation with explicit break detection and audit logging
- Frontend mission page, mission directory, registry entry, manifest update, and smoke test

## Institutional behavior delivered
- Post-trade tickets now preserve decision, allocation, strategy, and broker lineage
- Settlement confirmation updates internal ledgers instead of treating fills as final truth
- Reconciliation breaks are surfaced as governed exceptions rather than hidden drift
- The package structure was preserved exactly and only extended with QNT50007 files
