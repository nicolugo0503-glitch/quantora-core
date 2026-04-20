# QNT30508 — Broker persistence adapter
# Additive mission module only. No existing core files modified.

from typing import Any, Dict, List


class QNT30508BrokerPersistenceAdapter:
    def __init__(self, store: Any, execution_bridge: Any = None, alpaca_client: Any = None) -> None:
        self.store = store
        self.execution_bridge = execution_bridge
        self.alpaca_client = alpaca_client

    def _safe_get_orders(self) -> List[Dict[str, Any]]:
        if self.alpaca_client and hasattr(self.alpaca_client, "get_open_orders"):
            try:
                return list(self.alpaca_client.get_open_orders() or [])
            except Exception:
                return []
        return []

    def _safe_get_fills(self) -> List[Dict[str, Any]]:
        if self.alpaca_client and hasattr(self.alpaca_client, "get_recent_fills"):
            try:
                return list(self.alpaca_client.get_recent_fills() or [])
            except Exception:
                return []
        return []

    def _safe_get_positions(self) -> List[Dict[str, Any]]:
        if self.alpaca_client and hasattr(self.alpaca_client, "get_all_positions"):
            try:
                return list(self.alpaca_client.get_all_positions() or [])
            except Exception:
                return []
        return []

    def persist_live_broker_state(self) -> Dict[str, Any]:
        orders = self._safe_get_orders()
        fills = self._safe_get_fills()
        positions = self._safe_get_positions()

        if self.execution_bridge and hasattr(self.execution_bridge, "enrich_order_batch"):
            try:
                orders = self.execution_bridge.enrich_order_batch(orders)
            except Exception:
                pass

        if self.execution_bridge and hasattr(self.execution_bridge, "attach_execution_context_to_fills"):
            try:
                fills = self.execution_bridge.attach_execution_context_to_fills(fills)
            except Exception:
                pass

        if self.execution_bridge and hasattr(self.execution_bridge, "attribute_position_batch"):
            try:
                positions = self.execution_bridge.attribute_position_batch(positions)
            except Exception:
                pass

        for row in orders:
            self.store.append_order(row)
        for row in fills:
            self.store.append_fill(row)
        positions_snapshot = self.store.write_positions_snapshot(positions)

        return {
            "orders_persisted": len(orders),
            "fills_persisted": len(fills),
            "positions_snapshot_count": len(positions_snapshot.get("positions", [])),
            "positions_snapshot_updated_at": positions_snapshot.get("updated_at", ""),
        }
