QNT30503 — EXECUTION / FUND / ALPACA WIRING

PURPOSE
Replace the QNT30502 default in-memory endpoint store with an adapter that can read from your existing live system objects.

ADDS
- qnt30503_system_adapter.py
- router_binding_example.py
- system_mapping_contract.json

WHAT THIS DOES
- reads runtime state from the existing runtime engine when available
- reads positions and orders from the existing Alpaca/live client when available
- builds fund summary rows from the execution bridge or fund engine
- builds investor overview rows from the investor dashboard engine
- reads NAV from runtime state or NAV engine
- passes runtime control actions into the runtime safety layer when available

WHY THIS IS THE RIGHT NEXT STEP
QNT30502 exposed the backend endpoints.
QNT30503 makes those endpoints pull from real existing Quantora components instead of default demo state.

STABILITY
Additive only. No existing backend files are modified.
