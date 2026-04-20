QNT30494 — EXECUTION FUND INTEGRATION BRIDGE

PURPOSE
Add a non-invasive adapter layer that upgrades an existing Alpaca/live execution system
into a fund-aware Quantora capital system bridge.

ADDS
- execution_fund_integration_bridge.py
- sample_execution_context_mapping.json
- INTEGRATION_NOTES.md

CAPABILITIES
- order enrichment with fund / sleeve / strategy context
- position attribution back into fund hierarchy
- fill context attachment
- NAV input grouping by fund
- exposure summaries by fund
- downstream execution sync packet creation

WHY THIS EXISTS
The broker integration already exists.
This module changes its role from simple execution transport into a capital-accounting-aware system component.

STABILITY RULE
This mission is additive only.
No existing structure or core file is modified.
