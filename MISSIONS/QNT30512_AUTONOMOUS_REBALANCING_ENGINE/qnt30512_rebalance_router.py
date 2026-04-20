# QNT30512 — Rebalancing router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel


class RebalanceBuildRequest(BaseModel):
    target_positions: List[Dict[str, Any]]
    actual_positions: List[Dict[str, Any]]


class RebalanceExecuteRequest(BaseModel):
    dry_run: bool = True


def build_qnt30512_router(engine: Any, executor: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30512 Rebalancing"])

    @router.post("/api/rebalance/build")
    def build_plan(payload: RebalanceBuildRequest) -> Dict[str, Any]:
        return engine.build_rebalance_plan(
            target_positions=payload.target_positions,
            actual_positions=payload.actual_positions,
        )

    @router.get("/api/rebalance/plan")
    def get_plan() -> Dict[str, Any]:
        return engine.get_last_plan()

    @router.post("/api/rebalance/execute")
    def execute_plan(payload: RebalanceExecuteRequest) -> Dict[str, Any]:
        return executor.execute_last_plan(dry_run=payload.dry_run)

    @router.get("/api/rebalance/execution")
    def get_last_execution() -> Dict[str, Any]:
        return executor.get_last_execution()

    return router
