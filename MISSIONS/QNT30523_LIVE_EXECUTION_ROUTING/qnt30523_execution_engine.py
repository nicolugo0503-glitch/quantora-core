
# QNT30523 — Live Execution + Capital Routing (Alpaca-ready)

from datetime import datetime, timezone

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30523ExecutionEngine:
    def __init__(self, broker=None):
        self.broker = broker
        self.executions = []

    def execute_orders(self, orders, live=False):
        results = []
        for o in orders:
            if live and self.broker:
                try:
                    res = self.broker.submit_order(o)
                except Exception as e:
                    res = {"error": str(e), "order": o}
            else:
                res = {"simulated": True, "order": o}
            results.append(res)

        record = {
            "timestamp": _ts(),
            "live": live,
            "orders": results
        }
        self.executions.append(record)
        return record

    def get_executions(self):
        return self.executions[-100:]
