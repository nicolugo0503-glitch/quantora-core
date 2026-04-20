# Alpaca Env Wiring Fix Report

## What was fixed
The broker layer already had a safe internal paper fallback, but Railway env wiring was not explicit or operator-friendly.

## Changes
- added `connection_mode` persistence for Alpaca: `auto`, `stored`, `env`, `internal`
- added Railway env resolution support for:
  - `ALPACA_API_KEY`
  - `APCA_API_KEY_ID`
  - `ALPACA_SECRET_KEY`
  - `APCA_API_SECRET_KEY`
  - `ALPACA_BASE_URL`
  - `APCA_API_BASE_URL`
  - `ALPACA_PAPER`
- added `GET /broker/alpaca/env-status`
- added `POST /broker/alpaca/use-env`
- updated `POST /broker/alpaca/connect` so blank credentials can activate Railway env mode
- updated disconnect behavior to persist internal paper mode instead of leaving an ambiguous state
- updated the frontend broker panel with a `Use Railway Env` button and env status pills

## Expected behavior
- if Railway env vars are present, the broker can switch cleanly into env-backed Alpaca mode
- if env vars are missing, the panel stays stable and falls back to internal paper mode
- manual stored credentials still work and take precedence when explicitly connected
