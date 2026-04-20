# QNT30404 — Autonomous Treasury, Reserve, and Liquidity Command Layer

## Purpose
Build treasury control for reserve preservation, liquidity monitoring, treasury sweeps, and automatic balance defense across cash, reserves, and deployable capital.

## Included
- treasury status and ratio view
- policy updates
- treasury snapshot updates
- sweep execution
- auto-balance logic
- treasury action history
- sweep history
- frontend treasury command panel
- smoke test

## Core endpoints
- GET /treasury/status
- POST /treasury/policy/update
- POST /treasury/snapshot/update
- POST /treasury/sweep
- POST /treasury/auto-balance
- GET /treasury/actions
- GET /treasury/sweeps
- GET /treasury/audit

## Role in the system
This mission gives Quantora a treasury command layer that protects liquidity and reserves instead of treating capital as one undifferentiated pool.
