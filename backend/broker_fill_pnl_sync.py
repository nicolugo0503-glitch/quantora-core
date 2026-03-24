# Quantora QNT30333 - Broker Fill + PnL Sync
from datetime import datetime

class BrokerFillPnLSync:
    def __init__(self):
        self.fills = []
        self.pnl_snapshots = []

    def record_fill(self, fill: dict) -> dict:
        item = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "symbol": fill.get("symbol"),
            "side": fill.get("side"),
            "qty": fill.get("qty", 0),
            "fill_price": fill.get("fill_price", 0),
            "order_id": fill.get("order_id"),
            "status": "filled",
            "source": "broker",
        }
        self.fills.append(item)
        return item

    def sync_pnl(self, position: dict, last_price: float) -> dict:
        qty = float(position.get("qty", 0) or 0)
        avg_entry = float(position.get("avg_entry_price", 0) or 0)
        unrealized = round((last_price - avg_entry) * qty, 4)
        snapshot = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "symbol": position.get("symbol"),
            "qty": qty,
            "avg_entry_price": avg_entry,
            "last_price": last_price,
            "unrealized_pnl": unrealized,
            "source": "broker-sync",
        }
        self.pnl_snapshots.append(snapshot)
        return snapshot

    def get_fills(self):
        return list(self.fills)

    def get_pnl_snapshots(self):
        return list(self.pnl_snapshots)
