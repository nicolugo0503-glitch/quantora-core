QNT30424 rebuild using QNT30423 as last-known-good deployment baseline.

What was done:
- Kept the original QNT30423 deploy.ps1 and 0_DEPLOY_TO_GITHUB.bat unchanged.
- Layered in the QNT30424 feature files only:
  - backend/app/main.py
  - frontend/org_execution_capital_engine.html
  - backend/smoke_test_qnt30424.py
  - QNT30424_TRADE_LIFECYCLE_FILL_ENGINE_NOTES.md

Intent:
- Preserve the last deployment flow that worked for the user.
- Avoid the later PowerShell deploy helper regressions.
