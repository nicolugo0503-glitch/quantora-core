
# QNT30521 — Adaptive AI Allocation Layer

from datetime import datetime, timezone

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30521AdaptiveEngine:
    def __init__(self):
        self.weights = {}
        self.history = []

    def update_performance(self, asset: str, pnl: float):
        w = self.weights.get(asset, 1.0)
        if pnl > 0:
            w *= 1.1
        else:
            w *= 0.9
        self.weights[asset] = round(w, 4)
        return {"asset": asset, "new_weight": self.weights[asset]}

    def adaptive_allocate(self, capital: float):
        total = sum(self.weights.values()) or 1.0
        alloc = {k: round((v/total)*capital,2) for k,v in self.weights.items()}
        row = {"timestamp": _ts(), "allocations": alloc}
        self.history.append(row)
        return row

    def get_state(self):
        return {"weights": self.weights, "history": self.history[-50:]}
