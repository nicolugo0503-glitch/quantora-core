# QNT30366 — Release Normalization + Deployment Audit Fix

## Mission
Normalize the release identity, remove stale version drift, and give Quantora a production-verifiable audit layer for Railway deployments.

## Shipped
- `backend/release_audit.py`
- `frontend/release_audit_panel.html`
- `backend/smoke_test_qnt30366.py`

## Normalization
- FastAPI title normalized to QNT30366
- homepage title normalized to QNT30366
- homepage layer badge normalized to QNT30366
- stale QNT30332 / QNT30359 markers removed from main app and command center

## New endpoints
- `GET /release/status`
- `GET /release-audit/status`

## What it adds
- production release identity check
- endpoint coverage audit
- panel coverage audit
- stale marker detection
- direct deploy verification panel

## Validation
- compile checks passed
- smoke test passed
