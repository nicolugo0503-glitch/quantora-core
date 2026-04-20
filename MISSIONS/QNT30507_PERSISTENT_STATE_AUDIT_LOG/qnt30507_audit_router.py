# QNT30507 — Audit router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter


def build_qnt30507_router(store: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30507 Audit"])

    @router.get("/api/audit/runtime-state")
    def get_runtime_state() -> Dict[str, Any]:
        return store.load_state()

    @router.get("/api/audit/logs")
    def get_audit_logs(limit: int = 200) -> Dict[str, Any]:
        return {
            "rows": store.read_audit_log(limit=limit),
            "limit": limit,
        }

    return router
