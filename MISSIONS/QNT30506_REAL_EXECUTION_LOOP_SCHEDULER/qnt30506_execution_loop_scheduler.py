# QNT30506 — Real Execution Loop + Scheduler
# Additive mission module only. No existing core files modified.
#
# PURPOSE
# Provide a continuously running execution loop that can be controlled by the
# existing runtime controls and feed state into the live control panel.

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30506ExecutionLoopScheduler:
    def __init__(
        self,
        state_adapter: Any = None,
        cycle_runner: Optional[Callable[[], Dict[str, Any]]] = None,
        interval_seconds: float = 5.0,
    ) -> None:
        self.state_adapter = state_adapter
        self.cycle_runner = cycle_runner
        self.interval_seconds = float(interval_seconds)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.status: str = "idle"
        self.cycle_count: int = 0
        self.last_cycle_at: str = ""
        self.last_result: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []

    def _log(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.logs.append({
            "ts": _utc_now(),
            "event": event,
            "payload": payload or {},
        })
        self.logs = self.logs[-200:]

    def _default_cycle(self) -> Dict[str, Any]:
        runtime = {}
        funds = {}
        investors = {}
        exposure = {}

        if self.state_adapter is not None:
            try:
                runtime = self.state_adapter.get_runtime_state()
            except Exception as e:
                runtime = {"error": str(e)}

            try:
                funds = self.state_adapter.get_fund_summary()
            except Exception as e:
                funds = {"error": str(e)}

            try:
                investors = self.state_adapter.get_investor_overview()
            except Exception as e:
                investors = {"error": str(e)}

            try:
                exposure = self.state_adapter.get_exposure_summary()
            except Exception as e:
                exposure = {"error": str(e)}

        return {
            "runtime": runtime,
            "funds": funds,
            "investors": investors,
            "exposure": exposure,
            "cycle_timestamp": _utc_now(),
        }

    def _run_loop(self) -> None:
        self._log("loop_started", {"interval_seconds": self.interval_seconds})
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                self.status = "paused"
                time.sleep(0.25)
                continue

            self.status = "running"
            try:
                result = self.cycle_runner() if self.cycle_runner else self._default_cycle()
                with self._lock:
                    self.cycle_count += 1
                    self.last_cycle_at = _utc_now()
                    self.last_result = result
                self._log("cycle_completed", {
                    "cycle_count": self.cycle_count,
                    "last_cycle_at": self.last_cycle_at,
                })
            except Exception as e:
                self.status = "error"
                self._log("cycle_failed", {"error": str(e)})

            slept = 0.0
            while slept < self.interval_seconds and not self._stop_event.is_set():
                time.sleep(0.25)
                slept += 0.25

        self.status = "stopped"
        self._log("loop_stopped", {"cycle_count": self.cycle_count})

    def start(self) -> Dict[str, Any]:
        if self._thread and self._thread.is_alive():
            self._pause_event.clear()
            self.status = "running"
            self._log("loop_resume_requested")
            return {"ok": True, "status": self.status, "message": "loop already running"}

        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.status = "running"
        return {"ok": True, "status": self.status}

    def pause(self) -> Dict[str, Any]:
        self._pause_event.set()
        self.status = "paused"
        self._log("loop_paused")
        return {"ok": True, "status": self.status}

    def resume(self) -> Dict[str, Any]:
        self._pause_event.clear()
        self.status = "running"
        self._log("loop_resumed")
        return {"ok": True, "status": self.status}

    def kill(self) -> Dict[str, Any]:
        self._pause_event.clear()
        self._stop_event.set()
        self.status = "killed"
        self._log("loop_killed")
        return {"ok": True, "status": self.status}

    def set_interval(self, seconds: float) -> Dict[str, Any]:
        self.interval_seconds = float(seconds)
        self._log("interval_updated", {"interval_seconds": self.interval_seconds})
        return {"ok": True, "interval_seconds": self.interval_seconds}

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self.status,
                "cycle_count": self.cycle_count,
                "last_cycle_at": self.last_cycle_at,
                "interval_seconds": self.interval_seconds,
                "last_result": self.last_result,
                "logs_tail": self.logs[-20:],
            }
