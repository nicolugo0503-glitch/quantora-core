from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

class PerformanceRecordRequest(BaseModel):
    positions: Dict[str, float] = {}
    strategy_id: str = "core"
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

def build_qnt30534_router(engine):
    r = APIRouter(tags=["QNT30534 Performance"])

    @r.post("/api/performance-engine/record")
    def record(req: PerformanceRecordRequest):
        return engine.record_cycle(
            positions=req.positions,
            strategy_id=req.strategy_id,
            realized_pnl=req.realized_pnl,
            unrealized_pnl=req.unrealized_pnl,
        )

    @r.get("/api/performance-engine/summary")
    def summary():
        return engine.summary()

    @r.get("/api/performance-engine/history")
    def history():
        return engine.history()

    return r
