QNT30508 — BROKER ORDER / FILL PERSISTENCE

PURPOSE
Add durable storage for broker orders, fills, and attributed position snapshots so Quantora gains execution-history continuity and restart-safe broker records.

ADDS
- qnt30508_broker_persistence_store.py
- qnt30508_broker_persistence_adapter.py
- qnt30508_broker_persistence_router.py
- broker_persistence_binding_example.py
- broker_persistence_contract.json
- frontend/mission_qnt30508_broker_persistence.html

ALSO CHANGES
- frontend/index.html (adds QNT30508 Broker button)
- frontend/conversation_missions_hub.html (adds QNT30508 card)

PRIMARY ENDPOINTS
- POST /api/broker/persist-now
- GET /api/broker/orders
- GET /api/broker/fills
- GET /api/broker/positions-snapshot

WHAT THIS UNLOCKS
- durable broker order history
- durable fill history
- restart-safe position snapshots
- live UI visibility into broker persistence state

STABILITY
Additive only. Minimal frontend button/card patch.
