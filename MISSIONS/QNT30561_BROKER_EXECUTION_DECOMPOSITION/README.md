QNT30561 — BROKER EXECUTION DECOMPOSITION

ADDS
- backend/app/qnt30561_broker_router.py
- backend/app/qnt30561_live_execution_router.py
- frontend/mission_qnt30561_broker_execution_decomposition_center.html

UPGRADES
- broker Alpaca routes extracted from monolithic main.py into dedicated router
- live execution routes extracted from monolithic main.py into dedicated router
- legacy route aliases preserved for rollback safety

PURPOSE
- reduce concentration risk in backend/app/main.py
- isolate real broker and live execution surfaces behind dedicated route modules
- continue router-first modularization without breaking Quantora structure
