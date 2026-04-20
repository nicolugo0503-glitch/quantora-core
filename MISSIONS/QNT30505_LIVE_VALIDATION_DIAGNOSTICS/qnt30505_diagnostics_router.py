# QNT30505 — Live Validation + Diagnostics Router
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30505DiagnosticsAdapter:
    def __init__(self, state_adapter: Optional[Any] = None) -> None:
        self.state_adapter = state_adapter

    def build_validation_report(self) -> Dict[str, Any]:
        runtime = {}
        funds = {}
        investors = {}
        exposure = {}

        if self.state_adapter is not None:
            try:
                runtime = self.state_adapter.get_runtime_state() or {}
            except Exception as e:
                runtime = {"error": str(e)}

            try:
                funds = self.state_adapter.get_fund_summary() or {}
            except Exception as e:
                funds = {"error": str(e)}

            try:
                investors = self.state_adapter.get_investor_overview() or {}
            except Exception as e:
                investors = {"error": str(e)}

            try:
                exposure = self.state_adapter.get_exposure_summary() or {}
            except Exception as e:
                exposure = {"error": str(e)}

        runtime_ok = bool(runtime) and "error" not in runtime and "fallback" not in str(runtime.get("status", "")).lower() and "missing" not in str(runtime.get("status", "")).lower()
        funds_ok = bool(funds.get("sleeves")) and "error" not in funds
        investors_ok = bool(investors.get("rows")) and "error" not in investors
        exposure_ok = bool(exposure) and "error" not in exposure and "fallback" not in str(exposure.get("source", "")).lower()

        return {
            "timestamp": _utc_now(),
            "checks": {
                "runtime_live": runtime_ok,
                "fund_rows_live": funds_ok,
                "investor_rows_live": investors_ok,
                "exposure_live": exposure_ok,
            },
            "live_ready": all([runtime_ok, funds_ok, investors_ok, exposure_ok]),
            "runtime": runtime,
            "funds": funds,
            "investors": investors,
            "exposure": exposure,
        }


def build_qnt30505_router(adapter: Optional[QNT30505DiagnosticsAdapter] = None) -> APIRouter:
    diagnostics = adapter or QNT30505DiagnosticsAdapter()
    router = APIRouter(tags=["QNT30505 Diagnostics"])

    @router.get("/api/diagnostics/live-validation")
    def diagnostics_live_validation():
        return diagnostics.build_validation_report()

    @router.get("/api/diagnostics/health-summary")
    def diagnostics_health_summary():
        report = diagnostics.build_validation_report()
        return {
            "timestamp": report["timestamp"],
            "live_ready": report["live_ready"],
            "checks": report["checks"],
        }

    return router
