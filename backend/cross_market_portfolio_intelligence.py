from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30402 Autonomous Cross-Market Portfolio Intelligence Engine", version="1.0.0")

STATE = {
    "engine_mode": "active",
    "market_exposures": {
        "equities": {"notional": 420000.0, "pnl": 12500.0, "risk_score": 0.42},
        "crypto": {"notional": 210000.0, "pnl": 8200.0, "risk_score": 0.58},
        "forex": {"notional": 90000.0, "pnl": 1400.0, "risk_score": 0.36},
    },
    "cross_market_signals": [],
    "correlation_matrix": {},
    "portfolio_intelligence": {
        "gross_exposure": 720000.0,
        "net_exposure": 505000.0,
        "portfolio_risk_score": 0.47,
        "dominant_market": "equities",
        "concentration_warning": False,
    },
    "rebalance_suggestions": [],
    "audit": [],
}

class MarketExposureUpdate(BaseModel):
    market: str
    notional: float = Field(..., ge=0.0)
    pnl: float = 0.0
    risk_score: float = Field(..., ge=0.0, le=1.0)

class CorrelationInput(BaseModel):
    pairs: Dict[str, float]

class CrossMarketSignal(BaseModel):
    source_market: str
    target_market: str
    signal_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    message: str

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

def recompute_portfolio_intelligence():
    exposures = STATE["market_exposures"]
    gross = round(sum(v["notional"] for v in exposures.values()), 2)
    net = round(sum(max(v["notional"], 0) for v in exposures.values()) * 0.70, 2)
    weighted_risk = 0.0
    if gross > 0:
        weighted_risk = sum(v["notional"] * v["risk_score"] for v in exposures.values()) / gross
    dominant_market = max(exposures.items(), key=lambda kv: kv[1]["notional"])[0] if exposures else None
    dominant_share = exposures[dominant_market]["notional"] / gross if gross and dominant_market else 0.0
    STATE["portfolio_intelligence"] = {
        "gross_exposure": gross,
        "net_exposure": net,
        "portfolio_risk_score": round(weighted_risk, 6),
        "dominant_market": dominant_market,
        "concentration_warning": dominant_share > 0.60,
    }
    suggestions = []
    for market, data in exposures.items():
        if data["risk_score"] > 0.65:
            suggestions.append({
                "market": market,
                "action": "de-risk",
                "reason": "risk_score_above_threshold",
                "target_reduction_ratio": 0.15,
            })
        elif data["pnl"] > 0 and data["risk_score"] < 0.45:
            suggestions.append({
                "market": market,
                "action": "scale_selectively",
                "reason": "positive_pnl_with_contained_risk",
                "target_increase_ratio": 0.10,
            })
    if STATE["portfolio_intelligence"]["concentration_warning"] and dominant_market:
        suggestions.append({
            "market": dominant_market,
            "action": "diversify",
            "reason": "dominant_market_concentration",
            "target_reduction_ratio": 0.12,
        })
    STATE["rebalance_suggestions"] = suggestions

@app.get("/cross-market-intelligence/status")
def status():
    return {
        "mission": "QNT30402",
        "engine_mode": STATE["engine_mode"],
        "portfolio_intelligence": STATE["portfolio_intelligence"],
        "market_count": len(STATE["market_exposures"]),
        "signal_count": len(STATE["cross_market_signals"]),
        "rebalance_suggestion_count": len(STATE["rebalance_suggestions"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/cross-market-intelligence/exposure/update")
def update_exposure(payload: MarketExposureUpdate):
    STATE["market_exposures"][payload.market] = {
        "notional": payload.notional,
        "pnl": payload.pnl,
        "risk_score": payload.risk_score,
    }
    recompute_portfolio_intelligence()
    log_event("market_exposure_updated", {"market": payload.market, "notional": payload.notional, "risk_score": payload.risk_score})
    return {"status": "ok", "market_exposures": STATE["market_exposures"], "portfolio_intelligence": STATE["portfolio_intelligence"]}

@app.get("/cross-market-intelligence/exposures")
def exposures():
    return {"market_exposures": STATE["market_exposures"]}

@app.post("/cross-market-intelligence/correlations/update")
def update_correlations(payload: CorrelationInput):
    STATE["correlation_matrix"] = payload.pairs
    log_event("correlations_updated", {"count": len(payload.pairs)})
    return {"status": "ok", "correlation_matrix": STATE["correlation_matrix"]}

@app.get("/cross-market-intelligence/correlations")
def correlations():
    return {"correlation_matrix": STATE["correlation_matrix"]}

@app.post("/cross-market-intelligence/signal")
def ingest_signal(payload: CrossMarketSignal):
    record = payload.model_dump()
    record["signal_id"] = f"SIG-{uuid.uuid4().hex[:12]}"
    record["created_at"] = now()
    STATE["cross_market_signals"].append(record)
    STATE["cross_market_signals"] = STATE["cross_market_signals"][-300:]
    log_event("cross_market_signal_ingested", {
        "source_market": payload.source_market,
        "target_market": payload.target_market,
        "signal_type": payload.signal_type,
        "confidence": payload.confidence,
    })
    return {"status": "ok", "signal": record}

@app.get("/cross-market-intelligence/signals")
def signals():
    return {"signals": STATE["cross_market_signals"][::-1]}

@app.post("/cross-market-intelligence/rebalance/recommend")
def recommend_rebalance():
    recompute_portfolio_intelligence()
    decision = {
        "decision_id": f"DEC-{uuid.uuid4().hex[:12]}",
        "generated_at": now(),
        "portfolio_intelligence": STATE["portfolio_intelligence"],
        "suggestions": STATE["rebalance_suggestions"],
    }
    log_event("cross_market_rebalance_recommended", {"decision_id": decision["decision_id"], "suggestion_count": len(STATE["rebalance_suggestions"])})
    return {"status": "ok", "decision": decision}

@app.get("/cross-market-intelligence/rebalance-suggestions")
def rebalance_suggestions():
    return {"rebalance_suggestions": STATE["rebalance_suggestions"]}

@app.get("/cross-market-intelligence/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("cross_market_portfolio_intelligence.py", host="127.0.0.1", port=8010, reload=False)
