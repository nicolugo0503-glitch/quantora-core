# QNT50012 — Period Close Distribution Ledger + Investor Notice Finalization

## Objective
Seal the distribution accounting cycle for a reporting period by converting executed payables into a period-close ledger and requiring final investor notice evidence before close completion.

## Added
- backend/app/period_close_distribution_ledger/
- backend/app/models/period_close_distribution_ledger_models.py
- backend/app/state/period_close_distribution_ledger_state.json
- backend/app/qnt50012_period_close_distribution_ledger_investor_notice_finalization_router.py
- frontend/mission_qnt50012_period_close_distribution_ledger_investor_notice_finalization.html

## Core controls
- Period-close registration from executed distribution payables
- Ledger finalization with settlement break and attestation gates
- Investor notice finalization per investor
- Final period close lock after communications evidence completes
