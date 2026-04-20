QNT30519B — DYNAMIC REGISTRY FIX

WHY THIS EXISTS
The prior registry loader relied on a specific button-container selector that did not exist in the deployed UI.
As a result, the dynamic mission buttons never mounted.

WHAT THIS FIX DOES
- makes the loader selector-independent
- finds the existing "Conversation Missions" button
- injects a dedicated dynamic mission section immediately after it
- keeps the mission hub registry-driven
- preserves the single manifest source of truth

EXPECTED RESULT
After redeploy:
- QNT30511 Recon
- QNT30512 Rebalance
- QNT30513 Treasury
- QNT30514 Capital
- QNT30515 Reports
- QNT30516 Fees
- QNT30517 Multi-Fund
- QNT30518 Onboarding

should appear automatically beneath or immediately after the existing Conversation Missions area.
