QNT30510 — AUTOMATED NAV REFRESH + END-OF-DAY SNAPSHOTS

PURPOSE
Add current NAV persistence and end-of-day snapshot archiving so Quantora gains a durable NAV history layer.

ADDS
- qnt30510_nav_snapshot_store.py
- qnt30510_nav_refresh_service.py
- qnt30510_nav_router.py
- nav_binding_example.py
- nav_refresh_contract.json
- frontend/mission_qnt30510_nav_refresh.html

ALSO CHANGES
- frontend/index.html (adds QNT30510 NAV button)
- frontend/conversation_missions_hub.html (adds QNT30510 card)

PRIMARY ENDPOINTS
- POST /api/nav/refresh
- POST /api/nav/eod-snapshot
- GET /api/nav/current
- GET /api/nav/eod-snapshots

WHAT THIS UNLOCKS
- current NAV persistence
- end-of-day NAV archive
- one-snapshot-per-day EOD policy
- deployable NAV visibility in the frontend

STABILITY
Additive only. Minimal frontend button/card patch.
