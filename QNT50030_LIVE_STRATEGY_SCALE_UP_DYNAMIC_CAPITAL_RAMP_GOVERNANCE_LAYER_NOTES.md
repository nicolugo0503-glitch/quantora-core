# QNT50030 — Live Strategy Scale-Up + Dynamic Capital Ramp Governance Layer

## Objective
Increase live strategy capital only after governed re-entry has already been executed and the strategy is eligible for controlled scale-up.

## Institutional Controls
- Requires executed QNT50029 re-entry evidence by default.
- Blocks live ramp approval or execution while safe mode is enabled.
- Requires treasury capacity and risk clearance before dynamic scale-up.
- Supports optional performance-signal gating for institutional ramp governance.

## Primary Outputs
- Scale case register
- Ramp approval record
- Ramp execution event with release destination
- Audit trail for capital ramp governance review
