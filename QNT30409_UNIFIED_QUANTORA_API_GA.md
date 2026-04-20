# QNT30409 — Unified Quantora API Gateway & Module Router

## Purpose
Create an API gateway surface that maps major Quantora modules, tracks module health, records inter-module requests, and provides one routing registry above the full project.

## Included
- gateway status
- route registry
- route upsert endpoint
- module health registry
- request log
- demo gateway run
- audit trail
- frontend gateway panel
- smoke test

## Core endpoints
- GET /api-gateway/status
- GET /api-gateway/routes
- POST /api-gateway/route/upsert
- POST /api-gateway/module-health/update
- GET /api-gateway/module-health
- POST /api-gateway/request/log
- POST /api-gateway/demo/run
- GET /api-gateway/request-log
- GET /api-gateway/audit

## Role in the system
This mission gives Quantora one gateway registry above the merged project so major systems can be observed and routed through one API control surface.
