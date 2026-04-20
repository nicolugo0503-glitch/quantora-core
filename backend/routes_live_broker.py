from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from live_broker_execution import LiveBrokerExecution

router = APIRouter(prefix="/live-broker", tags=["live-broker"])
broker = LiveBrokerExecution()

class DecisionBody(BaseModel):
    symbol: str
    side: str = "buy"
    qty: float = 0
    mode: str = "paper"
    governance_approved: bool = False

class PositionBody(BaseModel):
    position: Dict[str, Any]
    last_price: float

@router.get("/status")
def status():
    return {
        "mission": "QNT30332",
        "layer": "qnt30332-live-market-broker-execution",
        "broker_execution_enabled": True,
        "routing_mode": "governed",
    }

@router.post("/route-order")
def route_order(body: DecisionBody):
    return broker.route_order(body.model_dump())

@router.post("/tp-sl-check")
def tp_sl_check(body: PositionBody):
    return broker.apply_tp_sl(body.position, body.last_price)

@router.get("/execution-log")
def execution_log():
    return {"items": broker.get_execution_log()}
