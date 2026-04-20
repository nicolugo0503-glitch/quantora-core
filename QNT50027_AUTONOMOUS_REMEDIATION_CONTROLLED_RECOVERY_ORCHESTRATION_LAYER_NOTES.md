# QNT50027 — Autonomous Remediation + Controlled Recovery Orchestration Layer

This mission adds a controlled institutional recovery surface that turns governed breach cases into executable remediation actions.

## Added
- Remediation action registry with breach and directive lineage
- Recovery authorization gate with severe-case supervisory dependency
- Controlled recovery cycle ledger with capital recovery and residual-risk tracking
- Context sync against breach, risk, treasury, and control loop layers

## Primary backend endpoints
- `GET /autonomous-remediation/health`
- `GET /autonomous-remediation/summary`
- `GET /autonomous-remediation/actions`
- `GET /autonomous-remediation/recoveries`
- `POST /autonomous-remediation/configure`
- `POST /autonomous-remediation/sync-context`
- `POST /autonomous-remediation/register-action`
- `POST /autonomous-remediation/authorize-recovery`
- `POST /autonomous-remediation/execute-recovery`
- `POST /autonomous-remediation/close-action`
- `POST /autonomous-remediation/reset`
