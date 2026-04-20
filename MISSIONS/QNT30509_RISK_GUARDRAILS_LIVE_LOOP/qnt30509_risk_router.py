# QNT30509 — Risk guardrails router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter


def build_qnt30509_router(guardrails: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30509 Risk Guardrails"])

    @router.get("/api/risk/report")
    def get_risk_report() -> Dict[str, Any]:
        if hasattr(guardrails, "get_last_report"):
            return guardrails.get_last_report()
        return {"error": "guardrails object missing get_last_report"}

    return router
