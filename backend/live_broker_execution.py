# Quantora QNT30332 - Live Market + Broker Execution
from datetime import datetime

class LiveBrokerExecution:
    def __init__(self):
        self.execution_log = []

    def route_order(self, decision: dict) -> dict:
        record = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "source": "strategy-engine",
            "symbol": decision.get("symbol"),
            "side": decision.get("side", "buy"),
            "qty": decision.get("qty", 0),
            "mode": decision.get("mode", "paper"),
            "governance_approved": bool(decision.get("governance_approved", False)),
            "status": "approved-for-routing" if decision.get("governance_approved") else "blocked-awaiting-governance",
        }
        self.execution_log.append(record)
        return record

    def sync_position(self, broker_position: dict) -> dict:
        return {
            "symbol": broker_position.get("symbol"),
            "qty": broker_position.get("qty"),
            "avg_entry_price": broker_position.get("avg_entry_price"),
            "market_value": broker_position.get("market_value"),
            "source": "broker",
        }

    def apply_tp_sl(self, position: dict, last_price: float) -> dict:
        tp = position.get("take_profit")
        sl = position.get("stop_loss")
        event = {"action": "hold", "reason": "within-range", "last_price": last_price}
        if tp is not None and last_price >= tp:
            event = {"action": "close", "reason": "take-profit", "last_price": last_price}
        if sl is not None and last_price <= sl:
            event = {"action": "close", "reason": "stop-loss", "last_price": last_price}
        return event

    def get_execution_log(self):
        return list(self.execution_log)
