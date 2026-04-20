# QNT30508 — Broker persistence router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter


def build_qnt30508_router(store: Any, adapter: Any = None) -> APIRouter:
    router = APIRouter(tags=["QNT30508 Broker Persistence"])

    @router.post("/api/broker/persist-now")
    def persist_now() -> Dict[str, Any]:
        if adapter is None:
            return {"ok": False, "error": "no broker persistence adapter bound"}
        result = adapter.persist_live_broker_state()
        return {"ok": True, "result": result}

    @router.get("/api/broker/orders")
    def get_orders(limit: int = 200) -> Dict[str, Any]:
        return {"rows": store.read_orders(limit=limit), "limit": limit}

    @router.get("/api/broker/fills")
    def get_fills(limit: int = 200) -> Dict[str, Any]:
        return {"rows": store.read_fills(limit=limit), "limit": limit}

    @router.get("/api/broker/positions-snapshot")
    def get_positions_snapshot() -> Dict[str, Any]:
        return store.read_positions_snapshot()

    return router
