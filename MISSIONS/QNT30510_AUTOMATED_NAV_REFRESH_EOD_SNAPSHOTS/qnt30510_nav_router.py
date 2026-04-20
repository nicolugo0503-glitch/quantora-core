# QNT30510 — NAV router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter


def build_qnt30510_router(store: Any, service: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30510 NAV Refresh"])

    @router.post("/api/nav/refresh")
    def refresh_nav() -> Dict[str, Any]:
        return {"ok": True, "result": service.refresh_current_nav()}

    @router.post("/api/nav/eod-snapshot")
    def force_eod_snapshot() -> Dict[str, Any]:
        return service.maybe_take_eod_snapshot(force=True)

    @router.get("/api/nav/current")
    def get_current_nav() -> Dict[str, Any]:
        return store.read_current_nav()

    @router.get("/api/nav/eod-snapshots")
    def get_eod_snapshots(limit: int = 200) -> Dict[str, Any]:
        return {
            "rows": store.read_eod_snapshots(limit=limit),
            "limit": limit,
        }

    return router
