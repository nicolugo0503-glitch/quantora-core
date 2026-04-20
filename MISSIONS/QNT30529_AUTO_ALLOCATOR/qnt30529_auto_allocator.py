# QNT30529 — Auto-Allocator (route capital to top strategies) audit-fixed

from datetime import datetime, timezone
from typing import Dict, Any, List


def _ts():
    return datetime.now(timezone.utc).isoformat()


class QNT30529AutoAllocator:
    def __init__(self, scorer=None):
        self.scorer = scorer
        self.last_allocation: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

    def allocate_to_top(self, ranked_strategies: List[Dict[str, Any]], total_capital: float, top_n: int = 3):
        ranked = list(ranked_strategies or [])[:max(int(top_n), 1)]
        score_sum = sum(max(float(r.get("score", 0.0)), 0.0) for r in ranked) or 1.0

        rows = []
        for row in ranked:
            strategy_id = row.get("strategy_id")
            score = max(float(row.get("score", 0.0)), 0.0)
            capital = round((score / score_sum) * float(total_capital), 2)
            rows.append({
                "strategy_id": strategy_id,
                "score": round(score, 4),
                "allocated_capital": capital,
            })

        payload = {
            "timestamp": _ts(),
            "top_n": int(top_n),
            "total_capital": round(float(total_capital), 2),
            "rows": rows,
            "allocation_count": len(rows),
            "source": "manual_ranking_input",
        }
        self.last_allocation = payload
        self.history.append(payload)
        self.history = self.history[-200:]
        return payload

    def allocate_from_scorer(self, total_capital: float, top_n: int = 3):
        if self.scorer is None or not hasattr(self.scorer, "top"):
            return {
                "timestamp": _ts(),
                "error": "scorer_not_bound",
                "top_n": int(top_n),
                "total_capital": round(float(total_capital), 2),
            }

        ranked = self.scorer.top(int(top_n))
        payload = self.allocate_to_top(ranked, total_capital, top_n)
        payload["source"] = "scorer_binding"
        self.last_allocation = payload
        if self.history:
            self.history[-1] = payload
        return payload

    def get_last_allocation(self) -> Dict[str, Any]:
        return self.last_allocation or {
            "timestamp": _ts(),
            "top_n": 0,
            "total_capital": 0.0,
            "rows": [],
            "allocation_count": 0,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history[-100:]
