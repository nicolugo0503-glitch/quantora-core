QNT30490 — LIVE DATA + EXECUTION BRIDGE

PURPOSE
Add an isolated bridge layer that converts real broker-style position and order payloads
into Quantora-native snapshots for fund accounting and integration flow execution.

ADDS
- live_execution_bridge.py
- sample_live_bridge_inputs.json

CAPABILITIES
- normalize broker positions
- normalize broker orders
- map symbols to strategies
- convert live positions into NAV-engine-compatible inputs
- build execution snapshots by fund
- feed live execution state into QNT30489 integration cycle

INTEGRATION INTENT
- read real positions and open orders from broker adapters (Alpaca first)
- map execution state into fund-aware accounting structures
- eliminate mock-only NAV inputs by using normalized live snapshots
- preserve all existing project files and structure

STABILITY RULE
This mission is additive only.
No existing structure or core file is modified.
