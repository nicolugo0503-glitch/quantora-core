
# QNT30526 — Risk Governor + Kill Switch

from datetime import datetime, timezone

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30526RiskGovernor:
    def __init__(self, max_position=10000, max_loss=-2000):
        self.max_position = max_position
        self.max_loss = max_loss
        self.killed = False
        self.events = []

    def evaluate(self, orders, current_pnl=0):
        if self.killed:
            return {"blocked": True, "reason": "kill_switch_active"}

        if current_pnl <= self.max_loss:
            self.killed = True
            return {"blocked": True, "reason": "max_loss_triggered"}

        filtered = []
        for o in orders:
            if abs(o.get("notional",0)) <= self.max_position:
                filtered.append(o)
            else:
                self.events.append({"ts":_ts(),"type":"blocked_position","order":o})

        return {"blocked": False, "orders": filtered}

    def kill_switch(self):
        self.killed = True
        return {"status":"killed"}

    def reset(self):
        self.killed = False
        return {"status":"reset"}

    def get_state(self):
        return {
            "killed": self.killed,
            "max_position": self.max_position,
            "max_loss": self.max_loss,
            "events": self.events[-50:]
        }
