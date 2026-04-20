# Quantora QNT30334 - Execution History + Operator Attribution
from datetime import datetime
from collections import defaultdict

class ExecutionHistoryAttribution:
    def __init__(self):
        self.history = []
        self.operator_stats = defaultdict(lambda: {
            "fills": 0,
            "realized_pnl": 0.0,
            "symbols": {},
        })

    def record_execution_event(self, event: dict) -> dict:
        item = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "operator_id": event.get("operator_id"),
            "strategy_id": event.get("strategy_id"),
            "symbol": event.get("symbol"),
            "side": event.get("side"),
            "qty": float(event.get("qty", 0) or 0),
            "fill_price": float(event.get("fill_price", 0) or 0),
            "realized_pnl": float(event.get("realized_pnl", 0) or 0),
            "source": event.get("source", "broker"),
        }
        self.history.append(item)

        op = item["operator_id"] or "unknown"
        stats = self.operator_stats[op]
        stats["fills"] += 1
        stats["realized_pnl"] += item["realized_pnl"]
        symbol = item["symbol"] or "unknown"
        stats["symbols"][symbol] = stats["symbols"].get(symbol, 0) + 1
        return item

    def operator_attribution(self, operator_id: str) -> dict:
        stats = self.operator_stats[operator_id]
        return {
            "operator_id": operator_id,
            "fills": stats["fills"],
            "realized_pnl": round(stats["realized_pnl"], 4),
            "top_symbols": sorted(
                [{"symbol": k, "fills": v} for k, v in stats["symbols"].items()],
                key=lambda x: x["fills"],
                reverse=True,
            ),
        }

    def reconcile_performance(self) -> dict:
        total_realized = round(sum(item["realized_pnl"] for item in self.history), 4)
        return {
            "events": len(self.history),
            "broker_reconciled_realized_pnl": total_realized,
            "operators": len(self.operator_stats),
        }

    def get_history(self):
        return list(self.history)
