QNT30493 — REAL CONTROL PANEL (WIRED)

PURPOSE
Add a wired operator command center that can display and mutate runtime state
without modifying the existing frontend or core architecture.

ADDS
- real_control_panel.html
- control_panel_state_adapter.js
- sample_operator_state.json

CAPABILITIES
- start / pause / resume / kill runtime controls
- active fund selector
- runtime state rendering
- NAV / PnL / fee display
- sleeve allocation table
- investor overview table
- event log
- browser-local state adapter for safe integration testing

INTEGRATION INTENT
- connect to QNT30491 runtime state snapshots
- consume QNT30489 / QNT30490 / QNT30491 outputs
- provide operator-facing dashboard behavior without editing existing UI structure
- preserve all project files and folders

STABILITY RULE
This mission is additive only.
No existing structure or core file is modified.
