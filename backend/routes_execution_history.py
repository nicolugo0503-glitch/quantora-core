from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from execution_history_attribution import ExecutionHistoryAttribution

router = APIRouter(prefix="/execution-history", tags=["execution-history"])
engine = ExecutionHistoryAttribution()

class ExecutionEventBody(BaseModel):
    operator_id: Optional[str] = None
    strategy_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    qty: float = 0
    fill_price: float = 0
    realized_pnl: float = 0
    source: str = "broker"

@router.get("/status")
def status():
    return {
        "mission": "QNT30334",
        "layer": "qnt30334-execution-history-attribution",
        "history_enabled": True,
        "operator_attribution_enabled": True,
        "broker_reconciliation_enabled": True,
    }

@router.post("/record")
def record(body: ExecutionEventBody):
    return engine.record_execution_event(body.model_dump())

@router.get("/list")
def list_events():
    return {"items": engine.get_history()}

@router.get("/operator/{operator_id}")
def operator_view(operator_id: str):
    return engine.operator_attribution(operator_id)

@router.get("/reconcile")
def reconcile():
    return engine.reconcile_performance()
