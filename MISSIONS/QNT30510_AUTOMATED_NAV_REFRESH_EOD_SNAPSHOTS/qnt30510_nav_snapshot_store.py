# QNT30510 — Automated NAV Refresh + End-of-Day Snapshots
# Additive mission module only. No existing core files modified.

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class QNT30510NAVSnapshotStore:
    def __init__(
        self,
        current_nav_file: str = "data/qnt30510_current_nav.json",
        eod_nav_file: str = "data/qnt30510_eod_nav_snapshots.jsonl",
    ) -> None:
        self.current_nav_file = current_nav_file
        self.eod_nav_file = eod_nav_file
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        os.makedirs(os.path.dirname(self.current_nav_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.eod_nav_file), exist_ok=True)

    def read_current_nav(self) -> Dict[str, Any]:
        if not os.path.exists(self.current_nav_file):
            return {"updated_at": "", "nav_snapshot": {}}
        try:
            with open(self.current_nav_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"updated_at": "", "nav_snapshot": {}}

    def write_current_nav(self, nav_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "updated_at": _utc_now(),
            "nav_snapshot": dict(nav_snapshot or {}),
        }
        with open(self.current_nav_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return payload

    def append_eod_snapshot(self, nav_snapshot: Dict[str, Any], note: str = "automated_eod_snapshot") -> Dict[str, Any]:
        row = {
            "day": _utc_day(),
            "timestamp": _utc_now(),
            "note": note,
            "nav_snapshot": dict(nav_snapshot or {}),
        }
        with open(self.eod_nav_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def read_eod_snapshots(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not os.path.exists(self.eod_nav_file):
            return []
        rows: List[Dict[str, Any]] = []
        with open(self.eod_nav_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]
