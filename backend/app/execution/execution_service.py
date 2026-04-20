from __future__ import annotations

from typing import Any, Dict

from backend.app.brokers.broker_factory import get_broker


class ExecutionService:
    def __init__(self, broker_name: str):
        self.broker = get_broker(broker_name)

    def execute_trade(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        return self.broker.place_order(envelope)

    def status(self, order_id: str) -> Dict[str, Any]:
        return self.broker.get_order_status(order_id)
