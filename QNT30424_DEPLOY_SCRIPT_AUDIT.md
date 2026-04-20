# QNT30424 Deploy Script Audit

Root cause:
- inherited deploy helper was stale and still labeled QNT30378
- it assumed a ready main ref and used a brittle PowerShell wrapper
- Windows PowerShell parsing caused repeated failures

Fix:
- replaced deploy flow with a pure batch script
- uses git add -A
- bootstraps local git identity if missing
- commits only when staged changes exist
- pushes with HEAD:main
