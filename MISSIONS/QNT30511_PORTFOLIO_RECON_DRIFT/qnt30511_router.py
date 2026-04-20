
from fastapi import APIRouter
from typing import Any, Dict

def build_qnt30511_router(engine: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30511 Reconciliation"])

    @router.get("/api/recon/report")
    def get_report() -> Dict[str, Any]:
        return engine.get_last_report()

    return router
