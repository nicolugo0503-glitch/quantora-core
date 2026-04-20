QNT30531 — PRODUCTION INTEGRATION + AUDIT FIX PASS

This mission fixes the critical findings from the QNT30530 full audit.

Implemented:
1. Integrated QNT30505–QNT30530 routers into the active deployment runtime via backend/app/qnt30531_integration.py
2. Added requests dependency
3. Fixed QNT30524 Alpaca adapter:
   - submit_order supports qty/notional
   - added get_all_positions()
   - added get_account()
   - added get_open_orders()
   - added get_recent_fills()
4. Fixed QNT30522 broken import in binding example
5. Fixed QNT30515 router to expose statement/distribution creation APIs
6. Fixed QNT30516 router to expose fee calculation API
7. Fixed QNT30529 by binding auto-allocator to scoring engine
8. Fixed QNT30530:
   - real background worker thread
   - start/stop lifecycle
   - risk gate now evaluates derived orders and live PnL
9. Added missing QNT30506 scheduler page
10. Added smoke endpoint: /api/audit/qnt30531-smoke

Important:
This is a production integration pass, not a UI redesign.
