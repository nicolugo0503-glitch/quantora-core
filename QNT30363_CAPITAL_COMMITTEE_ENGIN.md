# QNT30363 — Capital Committee Engine + Allocation Vote Compiler

## Mission
Build the institutional capital committee engine that governs allocation proposals through committee quorum, weighted voting, and compiled capital decisions.

## Shipped
- `backend/capital_committee_engine.py`
- `frontend/capital_committee_engine_panel.html`
- `backend/smoke_test_qnt30363.py`

## New endpoints
- `GET /capital-committee/status`
- `POST /capital-committee/committees/upsert`
- `POST /capital-committee/proposals/create`
- `POST /capital-committee/votes/cast`
- `POST /capital-committee/allocations/compile`

## What it adds
- committee registry with quorum and approval thresholds
- allocation proposal creation
- weighted committee voting
- automatic compile on quorum
- compiled recommended capital from approval ratios
- governance ledger events for committee actions

## Validation
- compile checks passed
- smoke test passed
