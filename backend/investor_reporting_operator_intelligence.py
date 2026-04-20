from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30397 Investor Reporting and Operator Intelligence Layer", version="1.0.0")

STATE = {
    "portfolio_snapshot": {
        "aum": 1000000.0,
        "realized_pnl": 15250.45,
        "unrealized_pnl": 3210.10,
        "net_pnl": 18460.55,
        "sharpe": 1.82,
        "max_drawdown": 0.073,
        "win_rate": 0.61,
        "trade_count": 128,
    },
    "strategy_rankings": [
        {"strategy_id": "alpha-exec-01", "score": 94.2, "realized_pnl": 8250.0, "sharpe": 2.11, "status": "leader"},
        {"strategy_id": "regime-alloc-02", "score": 88.7, "realized_pnl": 5110.0, "sharpe": 1.74, "status": "active"},
        {"strategy_id": "meanrev-03", "score": 73.4, "realized_pnl": 1890.0, "sharpe": 1.02, "status": "watch"},
    ],
    "operator_alerts": [
        {"severity": "info", "message": "Execution drift stable across paper venues."},
        {"severity": "warning", "message": "One strategy nearing drawdown threshold."}
    ],
    "investor_reports": [],
    "operator_briefs": [],
    "audit": [],
}

class PortfolioSnapshotUpdate(BaseModel):
    aum: Optional[float] = None
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    net_pnl: Optional[float] = None
    sharpe: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    trade_count: Optional[int] = None

class StrategyRankingBatch(BaseModel):
    rankings: List[Dict[str, Any]]

class InvestorReportRequest(BaseModel):
    period_label: str
    audience: str = "investor"
    include_operator_notes: bool = False

class OperatorBriefRequest(BaseModel):
    focus: str = "daily"
    include_risk: bool = True
    include_execution: bool = True
    include_capital: bool = True

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

def top_strategy():
    if not STATE["strategy_rankings"]:
        return None
    ranked = sorted(STATE["strategy_rankings"], key=lambda x: x.get("score", 0), reverse=True)
    return ranked[0]

@app.get("/reporting/status")
def status():
    return {
        "mission": "QNT30397",
        "portfolio_snapshot": STATE["portfolio_snapshot"],
        "top_strategy": top_strategy(),
        "operator_alert_count": len(STATE["operator_alerts"]),
        "investor_report_count": len(STATE["investor_reports"]),
        "operator_brief_count": len(STATE["operator_briefs"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/reporting/portfolio/update")
def update_portfolio(payload: PortfolioSnapshotUpdate):
    data = payload.model_dump(exclude_none=True)
    STATE["portfolio_snapshot"].update(data)
    log_event("portfolio_snapshot_updated", data)
    return {"status": "ok", "portfolio_snapshot": STATE["portfolio_snapshot"]}

@app.get("/reporting/portfolio")
def portfolio():
    return STATE["portfolio_snapshot"]

@app.post("/reporting/strategies/update")
def update_strategies(payload: StrategyRankingBatch):
    STATE["strategy_rankings"] = payload.rankings
    log_event("strategy_rankings_updated", {"count": len(payload.rankings)})
    return {"status": "ok", "rankings": STATE["strategy_rankings"]}

@app.get("/reporting/strategies")
def strategies():
    return {"rankings": STATE["strategy_rankings"]}

@app.get("/reporting/alerts")
def alerts():
    return {"alerts": STATE["operator_alerts"]}

@app.post("/reporting/investor-report/generate")
def generate_investor_report(payload: InvestorReportRequest):
    snapshot = STATE["portfolio_snapshot"]
    leader = top_strategy()
    report = {
        "report_id": f"INV-{uuid.uuid4().hex[:12]}",
        "period_label": payload.period_label,
        "audience": payload.audience,
        "generated_at": now(),
        "summary": {
            "aum": snapshot["aum"],
            "net_pnl": snapshot["net_pnl"],
            "sharpe": snapshot["sharpe"],
            "max_drawdown": snapshot["max_drawdown"],
            "win_rate": snapshot["win_rate"],
            "trade_count": snapshot["trade_count"],
            "top_strategy": leader,
        },
        "narrative": {
            "headline": f"Quantora delivered net PnL of {snapshot['net_pnl']} during {payload.period_label}.",
            "performance": f"Sharpe {snapshot['sharpe']}, drawdown {snapshot['max_drawdown']}, win rate {snapshot['win_rate']}.",
            "capital": f"AUM currently stands at {snapshot['aum']}.",
        },
        "operator_notes_included": payload.include_operator_notes,
    }
    if payload.include_operator_notes:
        report["operator_notes"] = STATE["operator_alerts"]
    STATE["investor_reports"].append(report)
    log_event("investor_report_generated", {"report_id": report["report_id"], "period_label": payload.period_label})
    return {"status": "ok", "report": report}

@app.get("/reporting/investor-reports")
def investor_reports():
    return {"reports": STATE["investor_reports"][::-1]}

@app.post("/reporting/operator-brief/generate")
def generate_operator_brief(payload: OperatorBriefRequest):
    snapshot = STATE["portfolio_snapshot"]
    brief = {
        "brief_id": f"OPS-{uuid.uuid4().hex[:12]}",
        "focus": payload.focus,
        "generated_at": now(),
        "sections": {
            "risk": {
                "included": payload.include_risk,
                "max_drawdown": snapshot["max_drawdown"],
                "win_rate": snapshot["win_rate"],
            },
            "execution": {
                "included": payload.include_execution,
                "alert_count": len(STATE["operator_alerts"]),
                "alerts": STATE["operator_alerts"] if payload.include_execution else [],
            },
            "capital": {
                "included": payload.include_capital,
                "aum": snapshot["aum"],
                "net_pnl": snapshot["net_pnl"],
                "top_strategy": top_strategy(),
            },
        }
    }
    STATE["operator_briefs"].append(brief)
    log_event("operator_brief_generated", {"brief_id": brief["brief_id"], "focus": payload.focus})
    return {"status": "ok", "brief": brief}

@app.get("/reporting/operator-briefs")
def operator_briefs():
    return {"briefs": STATE["operator_briefs"][::-1]}

@app.get("/reporting/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("investor_reporting_operator_intelligence.py", host="127.0.0.1", port=8010, reload=False)
