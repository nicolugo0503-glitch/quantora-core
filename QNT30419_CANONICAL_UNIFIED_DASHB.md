# QNT30419 — Canonical Unified Dashboard Runtime

This mission adds a single operator-facing runtime surface above the fragmented mission panels.

Included:
- `frontend/unified_dashboard_runtime.html`
- dashboard endpoints:
  - `/dashboard/runtime-summary`
  - `/dashboard/operator-brief`
  - `/dashboard/activity-feed`
  - `/dashboard/module-map`
- backend aggregator: `backend/qnt30419_unified_dashboard_runtime.py`
- command-center link to the unified dashboard runtime

Purpose:
- expose one canonical summary for readiness, billing posture, capital, active strategies, runtime modules, attribution, and recent activity
- reduce fragmented panel navigation by giving operators one top-level surface
