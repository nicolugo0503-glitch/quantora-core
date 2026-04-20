QNT30494 — EXECUTION ↔ FUND INTEGRATION BRIDGE

WHAT THIS MISSION DOES
This mission does NOT recreate the broker connector.
It upgrades the broker/execution layer into a fund-aware system adapter.

BEFORE
orders -> broker -> fills -> positions

AFTER
fund -> sleeve -> strategy -> orders -> broker -> positions -> NAV -> investors -> fees

MAIN JOBS
1. enrich outbound order payloads with:
   - fund_id
   - sleeve_id
   - strategy_id

2. attribute inbound positions/fills back into:
   - strategy
   - sleeve
   - fund

3. convert attributed positions into NAV-engine-ready inputs grouped by fund

4. provide exposure summaries by fund

INTENDED PLUG POINTS
- Existing Alpaca order submitter
- Existing position fetcher
- Existing fill / lifecycle reconciliation
- QNT30490 live execution bridge
- QNT30489 integration engine
- QNT30486 NAV engine

STABILITY
Additive only. No existing code paths or structures are modified.
