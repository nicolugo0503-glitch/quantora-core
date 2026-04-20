# QNT30506 — Scheduler control router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel


class SchedulerControlRequest(BaseModel):
    action: str
    interval_seconds: Optional[float] = None


def build_qnt30506_router(scheduler: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30506 Scheduler"])

    @router.get("/api/runtime/loop-state")
    def get_loop_state() -> Dict[str, Any]:
        return scheduler.get_state()

    @router.post("/api/runtime/loop-control")
    def post_loop_control(payload: SchedulerControlRequest) -> Dict[str, Any]:
        action = str(payload.action).lower().strip()

        if action == "start":
            return scheduler.start()
        if action == "pause":
            return scheduler.pause()
        if action == "resume":
            return scheduler.resume()
        if action == "kill":
            return scheduler.kill()
        if action == "set_interval":
            seconds = payload.interval_seconds if payload.interval_seconds is not None else scheduler.interval_seconds
            return scheduler.set_interval(seconds)

        return {"ok": False, "error": f"unsupported action: {action}"}

    return router
