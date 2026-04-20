# QNT30398 — Autonomous Oversight & Governance Control Layer

## Purpose
Create a supervisory governance layer that watches risk and execution signals, detects breaches, drives decisions, requests approvals, applies overrides, and can freeze the platform.

## Included
- oversight signal ingestion
- breach detection
- watchlist management
- governance approval requests and decisions
- policy override setting
- global freeze control
- decisions and control action logs
- frontend oversight/governance panel
- smoke test

## Core endpoints
- GET /governance/status
- POST /governance/thresholds/update
- POST /governance/signal/ingest
- GET /governance/watchlist
- GET /governance/breaches
- POST /governance/approval/request
- POST /governance/approval/decide
- POST /governance/override/set
- POST /governance/freeze
- GET /governance/decisions
- GET /governance/control-actions
- GET /governance/audit

## Role in the system
This mission gives Quantora a supervisory nervous system that can intervene above execution, capital, and strategy layers when governance conditions are breached.
