# QNT30408 — Unified Quantora State Fabric & Persistent Event Ledger

## Purpose
Create a persistent shared state fabric and event ledger so major Quantora systems can write to one common runtime memory and retain an event history across runs.

## Included
- persistent global state
- persistent module state
- persistent event ledger
- snapshot creation
- demo runtime write flow
- fabric and ledger file persistence
- frontend state fabric panel
- smoke test

## Core endpoints
- GET /state-fabric/status
- GET /state-fabric/global
- POST /state-fabric/global/update
- GET /state-fabric/modules
- POST /state-fabric/module/update
- POST /state-fabric/event/publish
- GET /state-fabric/ledger
- POST /state-fabric/snapshot
- GET /state-fabric/snapshots
- POST /state-fabric/demo/run

## Role in the system
This mission introduces a shared persistent runtime memory so Quantora can move from isolated module state toward a common operating fabric.
