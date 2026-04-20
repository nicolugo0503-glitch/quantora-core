# QNT30502 — Live Backend Control + State Endpoints
# Additive mission module only. No existing core files modified.
#
# PURPOSE
# Provide a drop-in FastAPI router exposing the frontend contract required by QNT30501.

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel


class RuntimeControlRequest(BaseModel):
    action: Literal["start", "pause", "resume", "kill"]


class RuntimeStateStore:
    def __init__(self) -> None:
        self.runtime_status: str = "simulation-fallback"
        self.cycle_count: int = 12
        self.nav: float = 734500.0
        self.active_fund: str = "FUND1"
        self.pnl: float = 23000.0
        self.last_updated: str = self._now()
        self.kill_switch: bool = False
        self.paused: bool = False

        self.fund_rows: List[Dict[str, Any]] = [
            {"sleeve": "Crypto Momentum", "capital": 500000.0},
            {"sleeve": "Low Risk Yield", "capital": 300000.0},
            {"sleeve": "AI Signals", "capital": 200000.0},
        ]

        self.investor_rows: List[Dict[str, Any]] = [
            {"investor": "Nicolas Capital", "fund": "FUND1", "market_value": 432000.0, "ownership_pct": 60.0},
            {"investor": "Atlas Growth", "fund": "FUND1", "market_value": 288000.0, "ownership_pct": 40.0},
        ]

        self.exposure_summary: Dict[str, Any] = {
            "pnl": 23000.0,
            "market_value": 507500.0,
            "source": "qnt30502-default-store",
        }

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_runtime_state(self) -> Dict[str, Any]:
        return {
            "status": self.runtime_status,
            "cycle_count": self.cycle_count,
            "nav": self.nav,
            "active_fund": self.active_fund,
            "pnl": self.pnl,
            "last_updated": self.last_updated,
            "kill_switch": self.kill_switch,
            "paused": self.paused,
        }

    def get_fund_summary(self) -> Dict[str, Any]:
        return {"sleeves": self.fund_rows, "last_updated": self.last_updated}

    def get_investor_overview(self) -> Dict[str, Any]:
        return {"rows": self.investor_rows, "last_updated": self.last_updated}

    def get_exposure_summary(self) -> Dict[str, Any]:
        payload = dict(self.exposure_summary)
        payload["last_updated"] = self.last_updated
        return payload

    def apply_action(self, action: str) -> Dict[str, Any]:
        if action == "start":
            self.runtime_status = "running"
            self.paused = False
            self.kill_switch = False
            self.cycle_count += 1
            self.nav += 1250.0
            self.pnl += 450.0
        elif action == "pause":
            self.runtime_status = "paused"
            self.paused = True
        elif action == "resume":
            self.runtime_status = "running"
            self.paused = False
            self.cycle_count += 1
            self.nav += 700.0
            self.pnl += 175.0
        elif action == "kill":
            self.runtime_status = "killed"
            self.kill_switch = True
            self.paused = False

        self.last_updated = self._now()
        self.exposure_summary["pnl"] = self.pnl

        return {
            "ok": True,
            "action": action,
            "runtime": self.get_runtime_state(),
        }


def build_qnt30502_router(state_store: Optional[RuntimeStateStore] = None) -> APIRouter:
    store = state_store or RuntimeStateStore()
    router = APIRouter(tags=["QNT30502 Live Control"])

    @router.get("/api/runtime/state")
    def get_runtime_state() -> Dict[str, Any]:
        return store.get_runtime_state()

    @router.get("/api/funds/summary")
    def get_funds_summary() -> Dict[str, Any]:
        return store.get_fund_summary()

    @router.get("/api/investors/overview")
    def get_investors_overview() -> Dict[str, Any]:
        return store.get_investor_overview()

    @router.get("/api/exposure/summary")
    def get_exposure_summary() -> Dict[str, Any]:
        return store.get_exposure_summary()

    @router.post("/api/runtime/control")
    def post_runtime_control(payload: RuntimeControlRequest) -> Dict[str, Any]:
        return store.apply_action(payload.action)

    # fallback aliases already supported by the QNT30501 client
    @router.get("/runtime/state")
    def get_runtime_state_alias() -> Dict[str, Any]:
        return store.get_runtime_state()

    @router.get("/funds/summary")
    def get_funds_summary_alias() -> Dict[str, Any]:
        return store.get_fund_summary()

    @router.get("/investors/overview")
    def get_investors_overview_alias() -> Dict[str, Any]:
        return store.get_investor_overview()

    @router.get("/exposure/summary")
    def get_exposure_summary_alias() -> Dict[str, Any]:
        return store.get_exposure_summary()

    @router.post("/api/qnt30501/runtime-control")
    def post_runtime_control_alias(payload: RuntimeControlRequest) -> Dict[str, Any]:
        return store.apply_action(payload.action)

    @router.get("/api/qnt30501/runtime-state")
    def get_runtime_state_alt() -> Dict[str, Any]:
        return store.get_runtime_state()

    @router.get("/api/qnt30501/fund-summary")
    def get_funds_summary_alt() -> Dict[str, Any]:
        return store.get_fund_summary()

    @router.get("/api/qnt30501/investor-overview")
    def get_investors_overview_alt() -> Dict[str, Any]:
        return store.get_investor_overview()

    @router.get("/api/qnt30501/exposure-summary")
    def get_exposure_summary_alt() -> Dict[str, Any]:
        return store.get_exposure_summary()

    return router
