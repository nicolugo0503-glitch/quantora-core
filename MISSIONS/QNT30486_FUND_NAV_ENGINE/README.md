QNT30486 — FUND NAV ENGINE

PURPOSE
Add an isolated institutional accounting module for fund-level NAV calculation.

ADDS
- fund_nav_engine.py
- sample_nav_inputs.json

CAPABILITIES
- cash + position market value aggregation
- liabilities deduction
- NAV computation
- NAV per share computation
- total PnL rollup from position snapshots

OUTPUT MODEL
FundNAVSnapshot {
  fund_id,
  gross_assets,
  liabilities,
  net_assets,
  nav,
  nav_per_share,
  total_shares
}

INTEGRATION INTENT
- read fund-level cash from treasury / ledger layer
- read positions from lifecycle / portfolio state
- read share counts from investor ledger layer
- compute institutional NAV snapshots without modifying core system files

STABILITY RULE
This mission is additive only.
No existing structure or core file is modified.
