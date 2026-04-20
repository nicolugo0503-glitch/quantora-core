QNT30532 — WARNING CLEANUP PASS

PURPOSE
Clean up the remaining warning-class audit findings after QNT30531.

WHAT THIS DOES
1. Adds legacy compatibility route:
   - GET /api/v1/reports/nav
   so older frontend panels do not break.

2. Documents normalized route matching for query-string frontend calls:
   - many remaining warnings were caused by literal audit matching of
     /api/path?param=value
     against backend declarations of
     /api/path

3. Provides a final cleanup checkpoint for operator verification.

OPERATOR CHECKLIST
- redeploy this ZIP
- verify /api/audit/qnt30531-smoke
- verify /api/v1/reports/nav
- open pages:
  - QNT30507 Audit
  - QNT30508 Broker
  - QNT30510 NAV
  - QNT30513 Treasury
  - QNT30514 Capital
  - QNT30518 Onboarding
- confirm query-string pages return data

WHY THIS MATTERS
This is the final cleanup pass to reduce warning-level noise before the next audit.
