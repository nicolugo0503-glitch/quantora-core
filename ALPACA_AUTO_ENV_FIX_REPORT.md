# Alpaca Auto Env Fix Report

## What changed
- startup now auto-detects Railway Alpaca env vars
- if env vars exist and no stored manual creds are set, Quantora switches to env mode automatically
- if env vars are missing, Quantora stays in clean internal paper fallback
- explicit internal mode is preserved
- stale packaged broker error state was removed from the shipped artifacts

## Result
After redeploy, you should not need to click `Use Railway Env` just to activate a valid Railway Alpaca config.
