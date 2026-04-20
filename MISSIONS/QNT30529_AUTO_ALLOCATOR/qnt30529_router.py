from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any


class AutoAllocRequest(BaseModel):
    ranked_strategies: List[Dict[str, Any]]
    total_capital: float
    top_n: int = 3


class AutoAllocScorerRequest(BaseModel):
    total_capital: float
    top_n: int = 3


def build_qnt30529_router(engine):
    r = APIRouter(tags=["QNT30529 Auto Allocator"])

    @r.post("/api/auto-allocator/run")
    def run_alloc(req: AutoAllocRequest):
        return engine.allocate_to_top(req.ranked_strategies, req.total_capital, req.top_n)

    @r.post("/api/auto-allocator/run-from-scorer")
    def run_alloc_from_scorer(req: AutoAllocScorerRequest):
        return engine.allocate_from_scorer(req.total_capital, req.top_n)

    @r.get("/api/auto-allocator/last")
    def last():
        return engine.get_last_allocation()

    @r.get("/api/auto-allocator/history")
    def history():
        return engine.get_history()

    return r
