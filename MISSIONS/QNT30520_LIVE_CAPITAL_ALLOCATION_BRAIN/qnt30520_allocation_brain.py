# QNT30520 — Live Capital Allocation Brain

from datetime import datetime, timezone
from typing import Dict, Any, List

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30520AllocationBrain:
    def __init__(self):
        self.decisions: List[Dict[str, Any]] = []

    def allocate(self, fund_id: str, capital: float, signals: Dict[str, float]):
        # simple scoring → weights
        total = sum(max(v, 0) for v in signals.values()) or 1.0
        allocations = {k: round((max(v,0)/total)*capital,2) for k,v in signals.items()}
        row = {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "capital": capital,
            "signals": signals,
            "allocations": allocations
        }
        self.decisions.append(row)
        self.decisions = self.decisions[-500:]
        return row

    def get_decisions(self):
        return self.decisions[-200:]