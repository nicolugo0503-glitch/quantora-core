# QNT30424.3 Forbidden Gate Hotfix

Patched the org execution submit path to avoid hard-blocking institutional/pro workspaces when the per-session billing state lags behind org-level billing configuration.

## Fix
- Resolve broker mode before billing gate evaluation
- Treat billing gate exceptions as non-blocking in workspace execution path
- Only raise `billing_subscription_inactive` for non-pro/non-institutional plans

## Intent
Preserve the execution write path during org-scoped testing while keeping plan checks for lower tiers.
