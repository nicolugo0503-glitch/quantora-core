from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from broker_fill_pnl_sync import BrokerFillPnLSync

router = APIRouter(prefix="/broker-sync", tags=["broker-sync"])
syncer = BrokerFillPnLSync()

class FillBody(BaseModel):
    symbol: str
    side: str
    qty: float
    fill_price: float
    order_id: str | None = None

class PositionBody(BaseModel):
    position: Dict[str, Any]
    last_price: float

@router.get("/status")
def status():
    return {
        "mission": "QNT30333",
        "layer": "qnt30333-broker-fill-pnl-sync",
        "broker_fill_sync_enabled": True,
        "pnl_sync_enabled": True,
    }

@router.post("/record-fill")
def record_fill(body: FillBody):
    return syncer.record_fill(body.model_dump())

@router.post("/sync-pnl")
def sync_pnl(body: PositionBody):
    return syncer.sync_pnl(body.position, body.last_price)

@router.get("/fills")
def fills():
    return {"items": syncer.get_fills()}

@router.get("/pnl-snapshots")
def pnl_snapshots():
    return {"items": syncer.get_pnl_snapshots()}
