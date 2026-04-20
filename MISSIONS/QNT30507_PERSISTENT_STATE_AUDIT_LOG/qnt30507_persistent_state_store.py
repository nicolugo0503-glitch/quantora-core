# QNT30507 — Persistent State + Audit Log
# Additive mission module only. No existing core files modified.

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30507PersistentStateStore:
    def __init__(
        self,
        state_file: str = "data/qnt30507_runtime_state.json",
        audit_file: str = "data/qnt30507_audit_log.jsonl",
    ) -> None:
        self.state_file = state_file
        self.audit_file = audit_file
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.audit_file), exist_ok=True)

    def _default_state(self) -> Dict[str, Any]:
        return {
            "status": "idle",
            "cycle_count": 0,
            "last_cycle_at": "",
            "interval_seconds": 5.0,
            "last_result": {},
            "last_updated": _utc_now(),
        }

    def load_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.state_file):
            state = self._default_state()
            self.save_state(state)
            return state
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            state = self._default_state()
            self.save_state(state)
            return state

    def save_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state = dict(state)
        state["last_updated"] = _utc_now()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return state

    def append_audit_event(self, event: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        row = {
            "ts": _utc_now(),
            "event": event,
            "payload": payload or {},
        }
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row

    def read_audit_log(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not os.path.exists(self.audit_file):
            return []
        rows: List[Dict[str, Any]] = []
        with open(self.audit_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]

    def recover_state_on_boot(self) -> Dict[str, Any]:
        state = self.load_state()
        self.append_audit_event("state_recovered_on_boot", {
            "status": state.get("status", "unknown"),
            "cycle_count": state.get("cycle_count", 0),
        })
        return state
