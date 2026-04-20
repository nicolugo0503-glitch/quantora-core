# QNT30422.1 — Strict Multi-Tenant Isolation Enforcement

This hardening pass extends the workspace foundation with explicit isolation controls.

## Included
- `/workspace/isolation/status`
- `/workspace/isolation/enforce`
- `/workspace/isolation/audit`
- bootstrap for `workspace_isolation_audit`
- bootstrap for `workspace_strategy_registry`
- automatic `organization_id` / `workspace_id` columns on known core tables when present
- active-workspace backfill for rows missing organization scope
- workspace UI isolation summary + enforcement button

## Goal
Move Quantora from workspace metadata to enforceable org-scoped persistence.

## Known scope
This patch hardens shared persistence and auditability. Legacy modules that return cross-org aggregates still need endpoint-by-endpoint scoping passes in future missions.
