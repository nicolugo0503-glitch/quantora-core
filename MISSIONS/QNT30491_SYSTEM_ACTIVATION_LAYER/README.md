QNT30491 — SYSTEM ACTIVATION LAYER

PURPOSE
Add an isolated runtime activation layer that turns Quantora's modular architecture
into a continuously executable simulation engine without changing any existing core files.

ADDS
- system_activation_runtime.py
- sample_activation_config.json

CAPABILITIES
- runtime cycle execution
- repeated simulation scheduling
- centralized QuantoraState snapshot
- event logging
- safety controls:
  - kill switch
  - pause switch
  - max drawdown guard

FLOW
broker data -> QNT30490 live bridge -> QNT30489 integration engine
-> NAV update -> dashboard update -> fee computation -> state/log refresh

INTEGRATION INTENT
- use normalized broker-style payloads from QNT30490
- execute full-cycle orchestration from QNT30489
- maintain last-known system state for future UI/runtime controls
- preserve all existing project files and structure

STABILITY RULE
This mission is additive only.
No existing structure or core file is modified.
