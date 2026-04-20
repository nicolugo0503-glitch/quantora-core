# QNT50009 — Investor Cash Confirmation + Treasury Release Authority

## What was added
- investor cash confirmation engine
- treasury-bound release authority registry
- transfer-level authorization lookup for investor-directed treasury movements
- release request, acknowledgement, and approval workflow
- state file, router, frontend mission page, mission registry entry, and smoke test

## Key integration point
QNT50008 treasury execution now blocks investor-directed cash transfers unless QNT50009 has issued active release authority for the specific treasury transfer ID.

## Protected transfer types
- `investor_redemption`
- `investor_distribution`
- `capital_return`
- destinations mapped to investor settlement bank
