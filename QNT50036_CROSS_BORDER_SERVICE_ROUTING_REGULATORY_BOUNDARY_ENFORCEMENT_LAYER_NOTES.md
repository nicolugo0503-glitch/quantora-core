# QNT50036 — Cross-Border Service Routing + Regulatory Boundary Enforcement Layer

This mission adds a governed control layer for routing services across jurisdictional boundaries.

## Core controls
- requires regional partition evidence when policy mandates it
- optional compliance clearance gating
- explicit regulatory boundary clearance on approval
- live execution blocked while safe mode is enabled
- audit-grade route case and routing event lineage

## Primary endpoints
- GET /cross-border-routing/health
- GET /cross-border-routing/summary
- POST /cross-border-routing/register-case
- POST /cross-border-routing/approve
- POST /cross-border-routing/execute
- POST /cross-border-routing/close-case
- POST /cross-border-routing/reset
