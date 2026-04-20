# QNT30389 — Persistent Data Layer and State Durability

## Purpose
Move Quantora beyond volatile in-memory state by adding durable storage, export/import flows, backups, and structured persistence for core business entities.

## Included
- JSON-backed persistent state store
- tenant, user, strategy, trade, allocation, subscription, and invoice durability
- backup creation
- full-state export
- full-state import
- collection record listing
- audit persistence
- frontend data-layer operations panel
- smoke test

## Core endpoints
- GET /data-layer/status
- POST /data-layer/tenant/upsert
- POST /data-layer/user/upsert
- POST /data-layer/strategy/upsert
- POST /data-layer/trade/upsert
- POST /data-layer/allocation/upsert
- POST /data-layer/subscription/upsert
- POST /data-layer/invoice/upsert
- GET /data-layer/export
- POST /data-layer/import
- POST /data-layer/backup/create
- GET /data-layer/records/{collection}
- GET /data-layer/audit

## Role in the system
This mission makes Quantora state survivable across process restarts and creates the first persistence boundary for commercial, portfolio, and execution records.

## What this unlocks
- durable tenant state
- recoverable commercial records
- exportable operating snapshots
- backup workflow foundation
- next-step migration path toward relational storage and production database design
