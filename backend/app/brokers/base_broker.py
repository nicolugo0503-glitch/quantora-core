from __future__ import annotations

from typing import Any, Dict


class BaseBroker:
    broker_name = 'base'
    supports_live = False

    def place_order(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        raise NotImplementedError
