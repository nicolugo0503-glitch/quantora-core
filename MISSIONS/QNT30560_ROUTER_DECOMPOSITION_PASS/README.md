QNT30560 — ROUTER DECOMPOSITION PASS

ADDS
- backend/app/qnt30560_auth_router.py
- backend/app/qnt30560_health_router.py
- frontend/mission_qnt30560_router_decomposition_center.html

UPGRADES
- auth routes extracted from monolithic main.py into dedicated router
- health routes extracted from monolithic main.py into dedicated router
- legacy aliases preserved for rollback safety

PURPOSE
- reduce concentration risk in backend/app/main.py
- establish the router extraction pattern for future decomposition passes
- preserve the current Quantora structure while improving maintainability
