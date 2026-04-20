from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30401 Autonomous Market Expansion & Multi-Asset Routing Layer", version="1.0.0")

STATE = {
    "routing_mode": "active",
    "supported_assets": {
        "equities": {"enabled": True, "venues": ["alpaca"]},
        "crypto": {"enabled": True, "venues": ["alpaca", "binance"]},
        "forex": {"enabled": False, "venues": ["ibkr"]},
        "futures": {"enabled": False, "venues": ["ibkr"]},
        "options": {"enabled": False, "venues": ["ibkr"]},
    },
    "routing_policies": {
        "equities": {"default_venue": "alpaca", "fallback": ["ibkr"]},
        "crypto": {"default_venue": "binance", "fallback": ["alpaca"]},
        "forex": {"default_venue": "ibkr", "fallback": []},
        "futures": {"default_venue": "ibkr", "fallback": []},
        "options": {"default_venue": "ibkr", "fallback": []},
    },
    "asset_universe": {},
    "route_history": [],
    "market_expansion_decisions": [],
    "audit": [],
}

class AssetInstrument(BaseModel):
    symbol: str
    asset_class: str
    venue_preferences: List[str] = []
    liquidity_score: float = Field(..., ge=0.0, le=1.0)
    execution_quality: float = Field(..., ge=0.0, le=1.0)
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None

class InstrumentBatch(BaseModel):
    instruments: List[AssetInstrument]

class RouteRequest(BaseModel):
    symbol: str
    asset_class: str
    side: str
    qty: float = Field(..., gt=0)
    urgency: str = "normal"
    preferred_venue: Optional[str] = None

class ExpansionDecision(BaseModel):
    asset_class: str
    enable: bool
    reason: str
    operator_id: str

def now():
    return datetime.utcnow().isoformat() + "Z"

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    })
    STATE["audit"] = STATE["audit"][-500:]

def choose_venue(symbol: str, asset_class: str, preferred_venue: Optional[str]) -> Dict[str, Any]:
    asset_cfg = STATE["supported_assets"].get(asset_class)
    if not asset_cfg:
        return {"status": "error", "reason": "unknown_asset_class"}
    if not asset_cfg.get("enabled"):
        return {"status": "error", "reason": "asset_class_disabled", "asset_class": asset_class}

    instrument = STATE["asset_universe"].get(symbol.upper())
    venues = list(asset_cfg.get("venues", []))
    policy = STATE["routing_policies"].get(asset_class, {})
    default_venue = policy.get("default_venue")
    fallbacks = policy.get("fallback", [])

    if preferred_venue and preferred_venue in venues:
        chosen = preferred_venue
    elif instrument and instrument.get("venue_preferences"):
        ordered = [v for v in instrument["venue_preferences"] if v in venues]
        chosen = ordered[0] if ordered else default_venue
    else:
        chosen = default_venue

    ordered_candidates = [chosen] + [v for v in fallbacks if v != chosen] + [v for v in venues if v != chosen and v not in fallbacks]
    ordered_candidates = [v for v in ordered_candidates if v]

    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "asset_class": asset_class,
        "chosen_venue": ordered_candidates[0] if ordered_candidates else None,
        "fallback_venues": ordered_candidates[1:],
        "enabled_venues": venues,
    }

@app.get("/multi-asset-routing/status")
def status():
    return {
        "mission": "QNT30401",
        "routing_mode": STATE["routing_mode"],
        "supported_assets": STATE["supported_assets"],
        "instrument_count": len(STATE["asset_universe"]),
        "route_count": len(STATE["route_history"]),
        "expansion_decision_count": len(STATE["market_expansion_decisions"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/multi-asset-routing/instruments/upsert")
def upsert_instruments(payload: InstrumentBatch):
    for instrument in payload.instruments:
        STATE["asset_universe"][instrument.symbol.upper()] = instrument.model_dump()
    log_event("instrument_universe_upserted", {"count": len(payload.instruments)})
    return {"status": "ok", "instrument_count": len(STATE["asset_universe"])}

@app.get("/multi-asset-routing/instruments")
def list_instruments():
    return {"instruments": list(STATE["asset_universe"].values())}

@app.post("/multi-asset-routing/route")
def route_order(payload: RouteRequest):
    if payload.side.lower() not in {"buy", "sell"}:
        return {"status": "error", "reason": "invalid_side"}

    route = choose_venue(payload.symbol, payload.asset_class, payload.preferred_venue)
    if route.get("status") != "ok":
        return route

    instrument = STATE["asset_universe"].get(payload.symbol.upper(), {})
    dispatch = {
        "route_id": f"RTE-{uuid.uuid4().hex[:12]}",
        "symbol": payload.symbol.upper(),
        "asset_class": payload.asset_class,
        "side": payload.side.lower(),
        "qty": payload.qty,
        "urgency": payload.urgency,
        "chosen_venue": route["chosen_venue"],
        "fallback_venues": route["fallback_venues"],
        "liquidity_score": instrument.get("liquidity_score"),
        "execution_quality": instrument.get("execution_quality"),
        "status": "routed",
        "timestamp": now(),
    }
    STATE["route_history"].append(dispatch)
    log_event("multi_asset_route_created", {
        "route_id": dispatch["route_id"],
        "symbol": dispatch["symbol"],
        "asset_class": dispatch["asset_class"],
        "chosen_venue": dispatch["chosen_venue"],
    })
    return {"status": "ok", "route": dispatch}

@app.post("/multi-asset-routing/expand")
def expand_market(payload: ExpansionDecision):
    if payload.asset_class not in STATE["supported_assets"]:
        return {"status": "error", "reason": "unknown_asset_class"}
    STATE["supported_assets"][payload.asset_class]["enabled"] = payload.enable
    decision = {
        "decision_id": f"EXP-{uuid.uuid4().hex[:12]}",
        "asset_class": payload.asset_class,
        "enable": payload.enable,
        "reason": payload.reason,
        "operator_id": payload.operator_id,
        "timestamp": now(),
    }
    STATE["market_expansion_decisions"].append(decision)
    log_event("market_expansion_decided", decision)
    return {"status": "ok", "decision": decision, "asset_state": STATE["supported_assets"][payload.asset_class]}

@app.get("/multi-asset-routing/routes")
def routes():
    return {"routes": STATE["route_history"][::-1]}

@app.get("/multi-asset-routing/expansion-history")
def expansion_history():
    return {"history": STATE["market_expansion_decisions"][::-1]}

@app.get("/multi-asset-routing/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("autonomous_market_expansion_multi_asset_routing.py", host="127.0.0.1", port=8010, reload=False)
