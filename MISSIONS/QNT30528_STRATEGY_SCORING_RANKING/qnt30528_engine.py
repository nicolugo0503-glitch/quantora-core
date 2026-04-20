# QNT30528 — Strategy Scoring + Ranking Engine

from datetime import datetime, timezone
from typing import Dict, Any, List

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30528ScoringEngine:
    def __init__(self):
        self.metrics: Dict[int, Dict[str, float]] = {}
        self.scores: Dict[int, float] = {}
        self.history: List[Dict[str, Any]] = []

    def update_metrics(self, strategy_id: int, pnl: float, drawdown: float, sharpe: float):
        m = self.metrics.get(strategy_id, {"pnl":0.0,"drawdown":0.0,"sharpe":0.0,"updates":0})
        m["pnl"] += pnl
        m["drawdown"] = min(m.get("drawdown", 0.0), drawdown)
        m["sharpe"] = (m.get("sharpe", 0.0) * m["updates"] + sharpe) / (m["updates"] + 1)
        m["updates"] += 1
        self.metrics[strategy_id] = m
        return m

    def compute_score(self, strategy_id: int):
        m = self.metrics.get(strategy_id)
        if not m:
            return {"error":"no_metrics"}
        # simple composite: reward pnl & sharpe, penalize drawdown
        score = (m["pnl"] * 0.5) + (m["sharpe"] * 100.0) + (m["drawdown"] * 0.5)
        self.scores[strategy_id] = round(score, 4)
        return {"strategy_id": strategy_id, "score": self.scores[strategy_id]}

    def rank(self):
        ranked = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        rows = [{"strategy_id": sid, "score": sc, "rank": i+1} for i,(sid,sc) in enumerate(ranked)]
        snap = {"timestamp": _ts(), "ranking": rows}
        self.history.append(snap)
        self.history = self.history[-200:]
        return snap

    def top(self, n: int = 5):
        ranked = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)[:n]
        return [{"strategy_id": sid, "score": sc} for sid, sc in ranked]

    def state(self):
        return {"metrics": self.metrics, "scores": self.scores, "history": self.history[-50:]}
