# QNT30530 — Live Fund Mode (scheduler + orchestrator) audit-fixed

import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def _ts():
    return datetime.now(timezone.utc).isoformat()


class QNT30530LiveFund:
    def __init__(self, closed_loop=None, risk=None):
        self.closed_loop = closed_loop
        self.risk = risk
        self.running = False
        self.interval_sec = 30
        self.last_run: Optional[Dict[str, Any]] = None
        self.last_payload: Dict[str, Any] = {}
        self.history = []
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def configure(self, interval_sec: int = 30):
        self.interval_sec = max(int(interval_sec), 1)
        return {"interval_sec": self.interval_sec}

    def start(self):
        if self.running:
            return {"running": True, "interval_sec": self.interval_sec, "status": "already_running"}
        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()
        return {"running": True, "interval_sec": self.interval_sec, "status": "started"}

    def stop(self):
        self.running = False
        self._stop_event.set()
        return {"running": False, "status": "stopped"}

    def _background_loop(self):
        while not self._stop_event.is_set():
            payload = dict(self.last_payload or {})
            if payload:
                try:
                    self.tick(payload)
                except Exception as e:
                    self._push({"timestamp": _ts(), "error": str(e), "stage": "background_tick"})
            time.sleep(self.interval_sec)

    def _extract_orders(self, payload: Dict[str, Any]):
        if payload.get("orders"):
            return list(payload.get("orders") or [])
        capital = float(payload.get("capital", 0.0) or 0.0)
        signals = payload.get("signals", {}) or {}
        total = sum(max(float(v), 0.0) for v in signals.values()) or 1.0
        rows = []
        for symbol, score in signals.items():
            notional = round((max(float(score), 0.0) / total) * capital, 2)
            rows.append({"symbol": symbol, "side": "buy" if notional > 0 else "hold", "notional": notional})
        return rows

    def _extract_current_pnl(self, payload: Dict[str, Any]):
        if payload.get("current_pnl") is not None:
            return float(payload.get("current_pnl", 0.0) or 0.0)
        pnl_map = payload.get("pnl_by_asset", {}) or {}
        return float(sum(float(v or 0.0) for v in pnl_map.values()))

    def tick(self, payload: Dict[str, Any]):
        self.last_payload = dict(payload or {})
        proposed_orders = self._extract_orders(payload)
        current_pnl = self._extract_current_pnl(payload)

        if self.risk:
            gate = self.risk.evaluate(proposed_orders, current_pnl)
            if gate.get("blocked"):
                out = {
                    "timestamp": _ts(),
                    "blocked": True,
                    "reason": gate.get("reason"),
                    "risk_state": self.risk.get_state() if hasattr(self.risk, "get_state") else {},
                }
                self.last_run = out
                self._push(out)
                return out
            payload = dict(payload or {})
            payload["orders"] = gate.get("orders", proposed_orders)
            payload["current_pnl"] = current_pnl

        if self.closed_loop:
            res = self.closed_loop.run_cycle(
                fund_id=payload.get("fund_id", "FUND1"),
                capital=float(payload.get("capital", 0.0) or 0.0),
                signals=payload.get("signals", {}) or {},
                pnl_by_asset=payload.get("pnl_by_asset", {}) or {},
                dry_run=bool(payload.get("dry_run", True)),
            )
        else:
            res = {"error": "closed_loop_not_bound"}

        out = {"timestamp": _ts(), "result": res}
        self.last_run = out
        self._push(out)
        return out

    def _push(self, row):
        with self._lock:
            self.history.append(row)
            self.history = self.history[-200:]

    def state(self):
        return {
            "running": self.running,
            "interval_sec": self.interval_sec,
            "last_run": self.last_run,
            "last_payload": self.last_payload,
            "history": self.history[-50:],
        }
