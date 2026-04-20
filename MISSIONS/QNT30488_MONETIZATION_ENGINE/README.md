QNT30488 — MONETIZATION ENGINE

PURPOSE
Add an isolated revenue and fee-calculation layer for Quantora without modifying
the current core project structure.

ADDS
- monetization_engine.py
- sample_monetization_inputs.json

CAPABILITIES
- subscription revenue computation
- management fee computation from AUM
- performance fee computation with hurdle support
- investor-level fee event allocation

REVENUE STREAMS SUPPORTED
- SaaS subscriptions
- capital management fees
- performance fees

INTEGRATION INTENT
- read investor market values from QNT30487 dashboard outputs
- read NAV / AUM context from QNT30486 fund NAV engine
- emit fee-event rows for future accounting / billing layers
- preserve all existing project files and structure

STABILITY RULE
This mission is additive only.
No existing structure or core file is modified.
