# QNT50008 — Treasury + Cash Mobility Control Layer

Quantora now controls treasury mobility after settlement instead of treating cash as an ungoverned residual.

## What was added
- institutional treasury state store with operating, broker buffer, and custody reserve accounts
- settlement-linked liquidity synchronization against QNT50007
- transfer staging, approval, and execution workflow with explicit audit trail
- treasury rebalance planner for internal cash reshaping to reserve policy targets

## Governance posture
- reserve floor and reserve buffer are protected before cash is released
- transfers can be forced into review when policy thresholds or reconciliation breaks are active
- cash movement now has mission-level lineage that can be inspected independently from execution and settlement
