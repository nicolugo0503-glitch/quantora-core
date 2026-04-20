from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

class CycleRequest(BaseModel):
    fund_id: str
    capital: float
    signals: Dict[str, float]
    pnl_by_asset: Dict[str, float]
    dry_run: bool = True

def build_qnt30522_router(engine):
    r = APIRouter(tags=["QNT30522 Closed Loop"])

    @r.post("/api/closed-loop/run")
    def run_cycle(payload: CycleRequest):
        return engine.run_cycle(
            fund_id=payload.fund_id,
            capital=payload.capital,
            signals=payload.signals,
            pnl_by_asset=payload.pnl_by_asset,
            dry_run=payload.dry_run,
        )

    @r.get("/api/closed-loop/cycles")
    def get_cycles():
        return engine.get_cycles()

    return r
