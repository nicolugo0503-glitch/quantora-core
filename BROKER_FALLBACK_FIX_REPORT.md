# Broker Fallback Fix Report

## What was fixed
The Alpaca Broker Layer was still showing disconnected / status error even after auth was repaired.

## Root cause
The deployed app was trying to use missing or broken Alpaca environment credentials and returning broker error state to the UI.

## Fix applied
- added an internal paper broker fallback snapshot
- added an internal paper broker view
- changed broker status behavior so missing credentials no longer surface as a broken panel
- changed soft broker refresh behavior so broken Alpaca env connectivity falls back cleanly to internal paper mode
- preserved explicit connect behavior for real manual broker connections

## Result
Fresh deploys now show a usable paper fallback instead of a broken broker panel when Alpaca env vars are unavailable or failing.

## Expected behavior after redeploy
- Risk Engine stays loaded
- Broker Layer no longer shows AUTH_REQUIRED
- Broker Layer no longer shows a broken error state on fresh Railway deploys
- Broker Layer falls back to internal paper mode unless real working Alpaca credentials are connected
