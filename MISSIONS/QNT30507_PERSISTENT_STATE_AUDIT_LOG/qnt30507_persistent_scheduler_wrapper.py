# QNT30507 — Scheduler persistence wrapper
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from MISSIONS.QNT30507_PERSISTENT_STATE_AUDIT_LOG.qnt30507_persistent_state_store import QNT30507PersistentStateStore


class QNT30507PersistentSchedulerWrapper:
    def __init__(self, scheduler: Any, store: QNT30507PersistentStateStore) -> None:
        self.scheduler = scheduler
        self.store = store

    def recover(self) -> Dict[str, Any]:
        persisted = self.store.recover_state_on_boot()
        try:
            self.scheduler.interval_seconds = float(persisted.get("interval_seconds", self.scheduler.interval_seconds))
            self.scheduler.cycle_count = int(persisted.get("cycle_count", self.scheduler.cycle_count))
            self.scheduler.last_cycle_at = persisted.get("last_cycle_at", self.scheduler.last_cycle_at)
            self.scheduler.last_result = persisted.get("last_result", self.scheduler.last_result)
            if persisted.get("status") in ("paused", "killed", "stopped", "idle"):
                self.scheduler.status = persisted.get("status")
        except Exception:
            pass
        return persisted

    def _persist(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self.scheduler.get_state()
        self.store.save_state({
            "status": state.get("status", "unknown"),
            "cycle_count": state.get("cycle_count", 0),
            "last_cycle_at": state.get("last_cycle_at", ""),
            "interval_seconds": state.get("interval_seconds", 5.0),
            "last_result": state.get("last_result", {}),
        })
        self.store.append_audit_event(event, payload)
        return state

    def start(self) -> Dict[str, Any]:
        result = self.scheduler.start()
        self._persist("loop_start", result)
        return result

    def pause(self) -> Dict[str, Any]:
        result = self.scheduler.pause()
        self._persist("loop_pause", result)
        return result

    def resume(self) -> Dict[str, Any]:
        result = self.scheduler.resume()
        self._persist("loop_resume", result)
        return result

    def kill(self) -> Dict[str, Any]:
        result = self.scheduler.kill()
        self._persist("loop_kill", result)
        return result

    def set_interval(self, seconds: float) -> Dict[str, Any]:
        result = self.scheduler.set_interval(seconds)
        self._persist("loop_set_interval", result)
        return result

    def get_state(self) -> Dict[str, Any]:
        state = self.scheduler.get_state()
        self.store.save_state({
            "status": state.get("status", "unknown"),
            "cycle_count": state.get("cycle_count", 0),
            "last_cycle_at": state.get("last_cycle_at", ""),
            "interval_seconds": state.get("interval_seconds", 5.0),
            "last_result": state.get("last_result", {}),
        })
        return state

    def record_cycle_result(self) -> Dict[str, Any]:
        state = self.scheduler.get_state()
        self.store.save_state({
            "status": state.get("status", "unknown"),
            "cycle_count": state.get("cycle_count", 0),
            "last_cycle_at": state.get("last_cycle_at", ""),
            "interval_seconds": state.get("interval_seconds", 5.0),
            "last_result": state.get("last_result", {}),
        })
        self.store.append_audit_event("cycle_snapshot_persisted", {
            "cycle_count": state.get("cycle_count", 0),
            "last_cycle_at": state.get("last_cycle_at", ""),
        })
        return state
