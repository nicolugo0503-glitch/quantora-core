# QNT30508 — Broker Order / Fill Persistence
# Additive mission module only. No existing core files modified.

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30508BrokerPersistenceStore:
    def __init__(
        self,
        orders_file: str = "data/qnt30508_orders.jsonl",
        fills_file: str = "data/qnt30508_fills.jsonl",
        positions_snapshot_file: str = "data/qnt30508_positions_snapshot.json",
    ) -> None:
        self.orders_file = orders_file
        self.fills_file = fills_file
        self.positions_snapshot_file = positions_snapshot_file
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        os.makedirs(os.path.dirname(self.orders_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.fills_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.positions_snapshot_file), exist_ok=True)

    def _append_jsonl(self, filepath: str, row: Dict[str, Any]) -> Dict[str, Any]:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def _read_jsonl(self, filepath: str, limit: int = 500) -> List[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return []
        rows: List[Dict[str, Any]] = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]

    def append_order(self, order_row: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(order_row)
        payload.setdefault("recorded_at", _utc_now())
        payload.setdefault("record_type", "order")
        return self._append_jsonl(self.orders_file, payload)

    def append_fill(self, fill_row: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(fill_row)
        payload.setdefault("recorded_at", _utc_now())
        payload.setdefault("record_type", "fill")
        return self._append_jsonl(self.fills_file, payload)

    def read_orders(self, limit: int = 500) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.orders_file, limit=limit)

    def read_fills(self, limit: int = 500) -> List[Dict[str, Any]]:
        return self._read_jsonl(self.fills_file, limit=limit)

    def write_positions_snapshot(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "updated_at": _utc_now(),
            "positions": list(positions),
        }
        with open(self.positions_snapshot_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return payload

    def read_positions_snapshot(self) -> Dict[str, Any]:
        if not os.path.exists(self.positions_snapshot_file):
            return {"updated_at": "", "positions": []}
        try:
            with open(self.positions_snapshot_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"updated_at": "", "positions": []}
