QNT30562 — CAPITAL GOVERNANCE DECOMPOSITION

ADDS
- backend/app/qnt30562_capital_router.py
- backend/app/qnt30562_governance_router.py
- frontend/mission_qnt30562_capital_governance_decomposition_center.html

UPGRADES
- capital ledger routes extracted from monolithic main.py into dedicated router
- governance, policy, and approvals routes extracted from monolithic main.py into dedicated router
- legacy route aliases preserved for rollback safety

PURPOSE
- continue modularization of the Quantora backend without breaking structure
- isolate capital truth and governance control surfaces behind dedicated route modules
- reduce concentration risk inside backend/app/main.py
