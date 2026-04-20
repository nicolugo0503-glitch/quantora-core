
# QNT30527 — Strategy Marketplace + External Capital Layer

from datetime import datetime, timezone

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30527Marketplace:
    def __init__(self):
        self.strategies = []
        self.allocations = []

    def register_strategy(self, name, creator):
        s = {"id": len(self.strategies)+1, "name": name, "creator": creator, "timestamp": _ts()}
        self.strategies.append(s)
        return s

    def allocate_capital(self, strategy_id, amount):
        a = {"strategy_id": strategy_id, "amount": amount, "timestamp": _ts()}
        self.allocations.append(a)
        return a

    def get_state(self):
        return {"strategies": self.strategies, "allocations": self.allocations}
