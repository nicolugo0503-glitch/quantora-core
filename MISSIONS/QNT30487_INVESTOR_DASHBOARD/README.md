QNT30487 — INVESTOR DASHBOARD

PURPOSE
Add an isolated investor reporting module that converts ledger ownership and fund NAV
into dashboard-ready investor views and statement outputs.

ADDS
- investor_dashboard.py
- sample_dashboard_inputs.json

CAPABILITIES
- investor position summary by fund
- shares owned
- ownership %
- market value
- net contributions
- unrealized gain
- single-investor statement payload

INTEGRATION INTENT
- read investor identities from investor ledger layer
- read share / cash movements from QNT30485 ledger events
- read NAV per share from QNT30486 fund NAV snapshots
- produce dashboard / statement JSON without modifying core system files

STABILITY RULE
This mission is additive only.
No existing structure or core file is modified.
