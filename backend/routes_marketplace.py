from fastapi import APIRouter
from .strategy_marketplace import list_strategies, publish_strategy, create_mandate, allocate, summary

router = APIRouter()

@router.get("/workspace/marketplace/strategies")
def api_list_strategies():
    return list_strategies()

@router.post("/workspace/marketplace/strategies/publish")
def api_publish(payload: dict):
    rec = publish_strategy(payload.get("name","Strategy"), payload.get("description",""), payload.get("risk_profile","balanced"))
    return {"status":"ok","strategy":rec}

@router.post("/workspace/marketplace/mandates/create")
def api_mandate(payload: dict):
    rec = create_mandate(payload.get("strategy_id"), payload.get("capital_target",0), payload.get("min_ticket",0))
    return {"status":"ok","mandate":rec}

@router.post("/workspace/marketplace/allocate")
def api_allocate(payload: dict):
    rec = allocate(payload.get("mandate_id"), payload.get("investor_name","LP"), payload.get("amount",0))
    return {"status":"ok","allocation":rec}

@router.get("/workspace/marketplace/summary")
def api_summary():
    return summary()
