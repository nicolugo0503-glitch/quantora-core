import json
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class QuantoraAutomationEngine:
    def __init__(
        self,
        state_path: str | Path,
        run_operator_cycle_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        now_iso_fn: Callable[[], str],
    ):
        self.state_path = Path(state_path)
        self.run_operator_cycle_fn = run_operator_cycle_fn
        self.now_iso_fn = now_iso_fn
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None

    def _utcnow(self) -> datetime:
        return datetime.utcnow().replace(microsecond=0)

    def _future_iso(self, seconds: int) -> str:
        return (self._utcnow() + timedelta(seconds=max(0, int(seconds)))).isoformat() + "Z"

    def _default_operator_config(self, operator_id: str) -> Dict[str, Any]:
        return {
            "operator_id": operator_id,
            "enabled": False,
            "execution_mode": "internal",
            "market_bias": "neutral",
            "interval_seconds": 30,
            "broker_reconcile_enabled": True,
            "pnl_sync_enabled": True,
            "failure_pause_seconds": 60,
            "max_consecutive_failures": 3,
            "retry_on_failure": True,
            "max_retry_attempts": 2,
            "retry_backoff_seconds": 5,
            "auto_strategy_optimizer_enabled": False,
            "auto_strategy_optimizer_max_active": 3,
            "auto_strategy_optimizer_min_score": 55.0,
            "auto_strategy_optimizer_pause_score": 35.0,
            "consecutive_failures": 0,
            "cycle_count": 0,
            "successful_cycles": 0,
            "degraded_cycles": 0,
            "failed_cycles": 0,
            "total_attempt_count": 0,
            "last_attempt_count": 0,
            "last_retry_count": 0,
            "last_run_at": None,
            "last_success_at": None,
            "next_run_at": None,
            "last_status": "idle",
            "health_status": "idle",
            "health_reason": None,
            "last_error": None,
            "last_result": {},
            "last_duration_ms": 0,
            "avg_duration_ms": 0,
            "paused_until": None,
            "recovery_required": False,
        }

    def _default_state(self) -> Dict[str, Any]:
        return {
            "worker": {
                "enabled": True,
                "poll_interval_seconds": 1,
                "stall_threshold_seconds": 45,
                "started_at": None,
                "heartbeat_at": None,
                "last_tick_at": None,
                "last_tick_started_at": None,
                "last_status": "idle",
                "last_error": None,
                "cycle_count": 0,
                "success_count": 0,
                "degraded_count": 0,
                "failure_count": 0,
                "restart_count": 0,
                "last_restart_at": None,
                "last_recovered_at": None,
                "last_cycle_duration_ms": 0,
                "avg_cycle_duration_ms": 0,
                "loop_lag_seconds": 0,
                "thread_alive": False,
            },
            "operators": {},
            "events": [],
        }

    def _parse_iso(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _now_aware(self) -> datetime:
        return datetime.now(timezone.utc).replace(microsecond=0)

    def _merge_defaults(self, current: Any, default: Any) -> Any:
        if isinstance(default, dict):
            merged = deepcopy(default)
            if isinstance(current, dict):
                for key, value in current.items():
                    merged[key] = self._merge_defaults(value, default[key]) if key in default else value
            return merged
        return current if current is not None else deepcopy(default)

    def _write_state(self, state: Dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    def _enrich_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        merged = self._merge_defaults(state or {}, self._default_state())
        operators = {}
        for operator_id, cfg in (merged.get("operators") or {}).items():
            operators[operator_id] = self._merge_defaults(cfg, self._default_operator_config(operator_id))
        merged["operators"] = operators
        merged["events"] = list(merged.get("events") or [])[:300]
        return merged

    def load_state(self) -> Dict[str, Any]:
        with self.lock:
            if not self.state_path.exists():
                state = self._default_state()
                self._write_state(state)
                return state
            try:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                state = self._default_state()
                self._write_state(state)
                return state
            state = self._enrich_state(state)
            return state

    def save_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            enriched = self._enrich_state(state)
            self._write_state(enriched)
        return enriched

    def ensure_operator(self, operator_id: str) -> Dict[str, Any]:
        state = self.load_state()
        state["operators"].setdefault(operator_id, self._default_operator_config(operator_id))
        self.save_state(state)
        return deepcopy(state["operators"][operator_id])

    def append_event(self, state: Dict[str, Any], event_type: str, operator_id: Optional[str], payload: Dict[str, Any]) -> None:
        event = {
            "event_id": f"auto_{int(time.time() * 1000)}",
            "timestamp": self.now_iso_fn(),
            "event_type": event_type,
            "operator_id": operator_id,
            "payload": payload,
        }
        state.setdefault("events", []).insert(0, event)
        state["events"] = state["events"][:300]

    def _worker_runtime(self, state: Dict[str, Any]) -> Dict[str, Any]:
        worker = deepcopy((state or {}).get("worker") or {})
        thread_alive = bool(self.worker_thread and self.worker_thread.is_alive())
        worker["thread_alive"] = thread_alive
        heartbeat_at = self._parse_iso(worker.get("heartbeat_at"))
        heartbeat_age = None
        if heartbeat_at:
            heartbeat_age = max(0.0, (self._now_aware() - heartbeat_at).total_seconds())
        worker["heartbeat_age_seconds"] = round(heartbeat_age or 0.0, 2)
        worker["stalled"] = bool(
            thread_alive
            and heartbeat_age is not None
            and heartbeat_age > max(5, int(worker.get("stall_threshold_seconds") or 45))
        )

        due = 0
        enabled = 0
        paused = 0
        unhealthy = 0
        for cfg in (state.get("operators") or {}).values():
            if cfg.get("enabled"):
                enabled += 1
            paused_until = self._parse_iso(cfg.get("paused_until"))
            if paused_until and paused_until > self._now_aware():
                paused += 1
            if cfg.get("enabled") and self._operator_due(cfg, force=False):
                due += 1
            if cfg.get("health_status") in {"error", "paused", "degraded"} or cfg.get("recovery_required"):
                unhealthy += 1
        worker["active_operators_count"] = enabled
        worker["due_operators_count"] = due
        worker["paused_operators_count"] = paused
        worker["unhealthy_operators_count"] = unhealthy
        return worker

    def configure_operator(self, operator_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        state = self.load_state()
        cfg = state["operators"].setdefault(operator_id, self._default_operator_config(operator_id))
        for key, value in (updates or {}).items():
            if value is not None and key in cfg:
                cfg[key] = value
        cfg["interval_seconds"] = max(5, int(cfg.get("interval_seconds") or 30))
        cfg["failure_pause_seconds"] = max(15, int(cfg.get("failure_pause_seconds") or 60))
        cfg["max_consecutive_failures"] = max(1, int(cfg.get("max_consecutive_failures") or 3))
        cfg["max_retry_attempts"] = max(0, int(cfg.get("max_retry_attempts") or 0))
        cfg["retry_backoff_seconds"] = max(1, int(cfg.get("retry_backoff_seconds") or 5))
        cfg["auto_strategy_optimizer_enabled"] = bool(cfg.get("auto_strategy_optimizer_enabled", False))
        cfg["auto_strategy_optimizer_max_active"] = max(1, int(cfg.get("auto_strategy_optimizer_max_active") or 3))
        cfg["auto_strategy_optimizer_min_score"] = max(0.0, min(100.0, float(cfg.get("auto_strategy_optimizer_min_score") or 55.0)))
        cfg["auto_strategy_optimizer_pause_score"] = max(0.0, min(100.0, float(cfg.get("auto_strategy_optimizer_pause_score") or 35.0)))
        cfg["retry_on_failure"] = bool(cfg.get("retry_on_failure", True))
        if cfg.get("enabled") and not cfg.get("next_run_at"):
            cfg["next_run_at"] = self.now_iso_fn()
        self.append_event(state, "operator_configured", operator_id, {"updates": updates, "config": deepcopy(cfg)})
        self.save_state(state)
        return deepcopy(cfg)

    def start_operator(self, operator_id: str, updates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        updates = updates or {}
        updates.update(
            {
                "enabled": True,
                "next_run_at": self.now_iso_fn(),
                "last_status": "scheduled",
                "health_status": "scheduled",
                "health_reason": None,
                "last_error": None,
                "paused_until": None,
                "recovery_required": False,
            }
        )
        return self.configure_operator(operator_id, updates)

    def stop_operator(self, operator_id: str) -> Dict[str, Any]:
        state = self.load_state()
        cfg = state["operators"].setdefault(operator_id, self._default_operator_config(operator_id))
        cfg["enabled"] = False
        cfg["next_run_at"] = None
        cfg["last_status"] = "stopped"
        cfg["health_status"] = "stopped"
        cfg["health_reason"] = None
        self.append_event(state, "operator_stopped", operator_id, {"config": deepcopy(cfg)})
        self.save_state(state)
        return deepcopy(cfg)

    def get_status(self, operator_id: Optional[str] = None) -> Dict[str, Any]:
        state = self.load_state()
        worker = self._worker_runtime(state)
        if operator_id:
            state["operators"].setdefault(operator_id, self._default_operator_config(operator_id))
            return {"worker": worker, "operator": state["operators"][operator_id], "health": self.get_health(operator_id)}
        return {"worker": worker, "operators": state.get("operators", {}), "events": state.get("events", []), "health": self.get_health()}

    def get_events(self, operator_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        state = self.load_state()
        items = state.get("events", [])
        if operator_id:
            items = [item for item in items if item.get("operator_id") in (None, operator_id)]
        return {"items": items[: max(1, min(limit, 300))], "count": len(items)}

    def _operator_due(self, cfg: Dict[str, Any], force: bool = False) -> bool:
        if force:
            return True
        if not cfg.get("enabled"):
            return False
        paused_until = self._parse_iso(cfg.get("paused_until"))
        if paused_until and paused_until > self._now_aware():
            return False
        due_at = self._parse_iso(cfg.get("next_run_at"))
        if due_at is None:
            return True
        return due_at <= self._now_aware()

    def _update_avg(self, current_avg: float, new_value: float, count: int) -> float:
        if count <= 1:
            return round(float(new_value), 2)
        return round((((float(current_avg) * (count - 1)) + float(new_value)) / count), 2)

    def run_operator_once(self, operator_id: str, force: bool = False) -> Dict[str, Any]:
        state = self.load_state()
        cfg = state["operators"].setdefault(operator_id, self._default_operator_config(operator_id))
        if not self._operator_due(cfg, force=force):
            return {"status": "skipped", "reason": "not_due", "operator": deepcopy(cfg)}

        worker = state.setdefault("worker", self._default_state()["worker"])
        worker["last_tick_started_at"] = self.now_iso_fn()
        attempts_allowed = 1 + (max(0, int(cfg.get("max_retry_attempts") or 0)) if cfg.get("retry_on_failure", True) else 0)
        cycle_started = time.time()
        last_error = None

        for attempt in range(1, attempts_allowed + 1):
            try:
                cfg["last_attempt_count"] = attempt
                cfg["last_retry_count"] = max(0, attempt - 1)
                result = self.run_operator_cycle_fn(operator_id, deepcopy(cfg)) or {}
                duration_ms = int((time.time() - cycle_started) * 1000)
                result_status = (result.get("status") or "completed").lower()
                cfg["last_run_at"] = self.now_iso_fn()
                cfg["last_success_at"] = cfg["last_run_at"]
                cfg["next_run_at"] = self._future_iso(max(5, int(cfg.get("interval_seconds") or 30)))
                cfg["last_status"] = result_status
                cfg["health_status"] = "healthy" if result_status == "completed" else "degraded"
                cfg["health_reason"] = None if result_status == "completed" else "non-critical stage degradation"
                cfg["last_error"] = None if result_status == "completed" else result.get("stage_errors")
                cfg["last_result"] = result
                cfg["consecutive_failures"] = 0
                cfg["paused_until"] = None
                cfg["recovery_required"] = False
                cfg["cycle_count"] = int(cfg.get("cycle_count") or 0) + 1
                cfg["successful_cycles"] = int(cfg.get("successful_cycles") or 0) + (1 if result_status == "completed" else 0)
                cfg["degraded_cycles"] = int(cfg.get("degraded_cycles") or 0) + (1 if result_status != "completed" else 0)
                cfg["total_attempt_count"] = int(cfg.get("total_attempt_count") or 0) + attempt
                cfg["last_duration_ms"] = duration_ms
                cfg["avg_duration_ms"] = self._update_avg(cfg.get("avg_duration_ms") or 0, duration_ms, int(cfg.get("cycle_count") or 1))

                worker["cycle_count"] = int(worker.get("cycle_count") or 0) + 1
                worker["success_count"] = int(worker.get("success_count") or 0) + (1 if result_status == "completed" else 0)
                worker["degraded_count"] = int(worker.get("degraded_count") or 0) + (1 if result_status != "completed" else 0)
                worker["last_tick_at"] = self.now_iso_fn()
                worker["heartbeat_at"] = self.now_iso_fn()
                worker["last_status"] = result_status
                worker["last_error"] = None if result_status == "completed" else "degraded-cycle"
                worker["last_cycle_duration_ms"] = duration_ms
                worker["avg_cycle_duration_ms"] = self._update_avg(worker.get("avg_cycle_duration_ms") or 0, duration_ms, int(worker.get("cycle_count") or 1))
                worker["loop_lag_seconds"] = 0

                event_name = "cycle_completed" if result_status == "completed" else "cycle_degraded"
                self.append_event(
                    state,
                    event_name,
                    operator_id,
                    {
                        "attempt": attempt,
                        "duration_ms": duration_ms,
                        "result": result,
                    },
                )
                self.save_state(state)
                return {"status": result_status, "operator": deepcopy(cfg), "result": result}
            except Exception as exc:
                last_error = str(exc)
                if attempt < attempts_allowed:
                    cfg["last_status"] = "retrying"
                    cfg["health_status"] = "degraded"
                    cfg["health_reason"] = f"retry {attempt} of {attempts_allowed - 1} pending"
                    cfg["last_error"] = last_error
                    worker["last_status"] = "retrying"
                    worker["last_error"] = last_error
                    self.append_event(
                        state,
                        "cycle_retry_scheduled",
                        operator_id,
                        {
                            "attempt": attempt,
                            "max_attempts": attempts_allowed,
                            "retry_backoff_seconds": max(1, int(cfg.get("retry_backoff_seconds") or 5)),
                            "error": last_error,
                        },
                    )
                    self.save_state(state)
                    time.sleep(min(max(1, int(cfg.get("retry_backoff_seconds") or 5)) * attempt, 5))
                    state = self.load_state()
                    cfg = state["operators"].setdefault(operator_id, self._default_operator_config(operator_id))
                    worker = state.setdefault("worker", self._default_state()["worker"])
                    continue

                duration_ms = int((time.time() - cycle_started) * 1000)
                cfg["last_run_at"] = self.now_iso_fn()
                cfg["last_status"] = "error"
                cfg["health_status"] = "error"
                cfg["health_reason"] = last_error
                cfg["last_error"] = last_error
                cfg["failed_cycles"] = int(cfg.get("failed_cycles") or 0) + 1
                cfg["consecutive_failures"] = int(cfg.get("consecutive_failures") or 0) + 1
                cfg["total_attempt_count"] = int(cfg.get("total_attempt_count") or 0) + attempt
                cfg["last_attempt_count"] = attempt
                cfg["last_retry_count"] = max(0, attempt - 1)
                cfg["last_duration_ms"] = duration_ms
                if cfg["consecutive_failures"] >= max(1, int(cfg.get("max_consecutive_failures") or 3)):
                    pause_seconds = max(15, int(cfg.get("failure_pause_seconds") or 60))
                    cfg["paused_until"] = self._future_iso(pause_seconds)
                    cfg["next_run_at"] = cfg["paused_until"]
                    cfg["health_status"] = "paused"
                    cfg["health_reason"] = f"failure threshold reached; paused for {pause_seconds}s"
                    cfg["recovery_required"] = True
                else:
                    next_retry = max(5, int(cfg.get("retry_backoff_seconds") or 5))
                    cfg["next_run_at"] = self._future_iso(next_retry)

                worker["failure_count"] = int(worker.get("failure_count") or 0) + 1
                worker["last_tick_at"] = self.now_iso_fn()
                worker["heartbeat_at"] = self.now_iso_fn()
                worker["last_status"] = "error"
                worker["last_error"] = last_error
                worker["last_cycle_duration_ms"] = duration_ms
                self.append_event(
                    state,
                    "cycle_error",
                    operator_id,
                    {
                        "error": last_error,
                        "consecutive_failures": cfg["consecutive_failures"],
                        "attempts_used": attempt,
                        "duration_ms": duration_ms,
                        "paused_until": cfg.get("paused_until"),
                    },
                )
                self.save_state(state)
                return {"status": "error", "operator": deepcopy(cfg), "error": last_error}

        return {"status": "error", "operator": deepcopy(cfg), "error": last_error or "unknown"}

    def tick(self, operator_id: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        state = self.load_state()
        summaries = []
        if operator_id:
            state["operators"].setdefault(operator_id, self._default_operator_config(operator_id))
            target_ids = [operator_id]
        else:
            target_ids = list(state.get("operators", {}).keys())
        for op_id in target_ids:
            summaries.append(self.run_operator_once(op_id, force=force))
        worker = self._worker_runtime(self.load_state())
        return {"worker": worker, "results": summaries, "count": len(summaries)}

    def get_metrics(self, operator_id: Optional[str] = None) -> Dict[str, Any]:
        state = self.load_state()
        worker = self._worker_runtime(state)
        operators = []
        selected = state.get("operators", {})
        if operator_id:
            selected = {operator_id: selected.get(operator_id, self._default_operator_config(operator_id))}
        for op_id, cfg in selected.items():
            total_cycles = int(cfg.get("cycle_count") or 0) + int(cfg.get("failed_cycles") or 0)
            success_cycles = int(cfg.get("successful_cycles") or 0)
            degraded_cycles = int(cfg.get("degraded_cycles") or 0)
            operators.append(
                {
                    "operator_id": op_id,
                    "enabled": bool(cfg.get("enabled")),
                    "last_status": cfg.get("last_status"),
                    "health_status": cfg.get("health_status"),
                    "cycle_count": int(cfg.get("cycle_count") or 0),
                    "successful_cycles": success_cycles,
                    "degraded_cycles": degraded_cycles,
                    "failed_cycles": int(cfg.get("failed_cycles") or 0),
                    "success_rate_pct": round((success_cycles / total_cycles) * 100, 2) if total_cycles > 0 else 0.0,
                    "avg_duration_ms": round(float(cfg.get("avg_duration_ms") or 0), 2),
                    "last_duration_ms": int(cfg.get("last_duration_ms") or 0),
                    "consecutive_failures": int(cfg.get("consecutive_failures") or 0),
                    "retry_budget": {
                        "retry_on_failure": bool(cfg.get("retry_on_failure")),
                        "max_retry_attempts": int(cfg.get("max_retry_attempts") or 0),
                        "retry_backoff_seconds": int(cfg.get("retry_backoff_seconds") or 0),
                    },
                    "last_success_at": cfg.get("last_success_at"),
                    "next_run_at": cfg.get("next_run_at"),
                }
            )
        return {
            "worker": {
                "cycle_count": int(worker.get("cycle_count") or 0),
                "success_count": int(worker.get("success_count") or 0),
                "degraded_count": int(worker.get("degraded_count") or 0),
                "failure_count": int(worker.get("failure_count") or 0),
                "avg_cycle_duration_ms": round(float(worker.get("avg_cycle_duration_ms") or 0), 2),
                "last_cycle_duration_ms": int(worker.get("last_cycle_duration_ms") or 0),
                "restart_count": int(worker.get("restart_count") or 0),
                "thread_alive": bool(worker.get("thread_alive")),
                "stalled": bool(worker.get("stalled")),
                "heartbeat_at": worker.get("heartbeat_at"),
                "heartbeat_age_seconds": worker.get("heartbeat_age_seconds"),
            },
            "operators": operators,
        }

    def get_health(self, operator_id: Optional[str] = None) -> Dict[str, Any]:
        state = self.load_state()
        worker = self._worker_runtime(state)
        operators = state.get("operators", {})
        if operator_id:
            operators = {operator_id: operators.get(operator_id, self._default_operator_config(operator_id))}
        unhealthy = [cfg for cfg in operators.values() if cfg.get("health_status") in {"error", "paused"} or cfg.get("recovery_required")]
        degraded = [cfg for cfg in operators.values() if cfg.get("health_status") == "degraded"]

        if not worker.get("enabled"):
            overall = "stopped"
            reason = "worker disabled"
        elif not worker.get("thread_alive"):
            overall = "degraded"
            reason = "worker thread not alive"
        elif worker.get("stalled"):
            overall = "degraded"
            reason = "worker heartbeat stalled"
        elif unhealthy:
            overall = "degraded"
            reason = "operator recovery required"
        elif degraded:
            overall = "degraded"
            reason = "non-critical stage degradation detected"
        else:
            overall = "healthy"
            reason = "automation loop healthy"

        return {
            "status": overall,
            "reason": reason,
            "worker": worker,
            "summary": {
                "operators_total": len(operators),
                "operators_unhealthy": len(unhealthy),
                "operators_degraded": len(degraded),
                "operators_active": int(worker.get("active_operators_count") or 0),
                "operators_due": int(worker.get("due_operators_count") or 0),
                "operators_paused": int(worker.get("paused_operators_count") or 0),
            },
            "operators": [
                {
                    "operator_id": cfg.get("operator_id"),
                    "enabled": cfg.get("enabled"),
                    "last_status": cfg.get("last_status"),
                    "health_status": cfg.get("health_status"),
                    "health_reason": cfg.get("health_reason"),
                    "consecutive_failures": cfg.get("consecutive_failures"),
                    "paused_until": cfg.get("paused_until"),
                    "last_success_at": cfg.get("last_success_at"),
                    "next_run_at": cfg.get("next_run_at"),
                }
                for cfg in operators.values()
            ],
        }

    def recover(
        self,
        operator_id: Optional[str] = None,
        restart_worker: bool = True,
        clear_failures: bool = True,
        run_immediately: bool = False,
    ) -> Dict[str, Any]:
        state = self.load_state()
        target_ids = [operator_id] if operator_id else list(state.get("operators", {}).keys())
        recovered = []
        for op_id in target_ids:
            cfg = state["operators"].setdefault(op_id, self._default_operator_config(op_id))
            if clear_failures:
                cfg["consecutive_failures"] = 0
                cfg["paused_until"] = None
                cfg["last_error"] = None
                cfg["health_reason"] = None
                cfg["recovery_required"] = False
            if cfg.get("enabled") or run_immediately:
                cfg["next_run_at"] = self.now_iso_fn()
                cfg["last_status"] = "scheduled"
                cfg["health_status"] = "scheduled"
            recovered.append(op_id)
            self.append_event(state, "operator_recovered", op_id, {"clear_failures": clear_failures, "run_immediately": run_immediately})

        state.setdefault("worker", self._default_state()["worker"])
        state["worker"]["last_recovered_at"] = self.now_iso_fn()
        self.save_state(state)

        if restart_worker and not (self.worker_thread and self.worker_thread.is_alive()):
            self.start_worker()

        recovery_result = {
            "status": "recovered",
            "recovered_operators": recovered,
            "worker_restarted": bool(restart_worker),
            "health": self.get_health(operator_id),
        }
        if run_immediately and operator_id:
            recovery_result["run_once"] = self.tick(operator_id=operator_id, force=True)
        return recovery_result

    def start_worker(self) -> None:
        with self.lock:
            if self.worker_thread and self.worker_thread.is_alive():
                return
            state = self.load_state()
            worker = state.setdefault("worker", self._default_state()["worker"])
            if worker.get("started_at"):
                worker["restart_count"] = int(worker.get("restart_count") or 0) + 1
                worker["last_restart_at"] = self.now_iso_fn()
            else:
                worker["started_at"] = self.now_iso_fn()
            worker["heartbeat_at"] = self.now_iso_fn()
            worker["last_status"] = "running"
            worker["last_error"] = None
            worker["thread_alive"] = True
            self.append_event(state, "worker_started", None, {"restart_count": worker.get("restart_count", 0)})
            self.save_state(state)
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._worker_loop, name="quantora-automation", daemon=True)
            self.worker_thread.start()

    def stop_worker(self) -> None:
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3)
        state = self.load_state()
        worker = state.setdefault("worker", self._default_state()["worker"])
        worker["last_status"] = "stopped"
        worker["thread_alive"] = False
        self.append_event(state, "worker_stopped", None, {})
        self.save_state(state)

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            started = time.time()
            try:
                state = self.load_state()
                worker = state.setdefault("worker", self._default_state()["worker"])
                worker["heartbeat_at"] = self.now_iso_fn()
                worker["last_tick_started_at"] = self.now_iso_fn()
                worker["thread_alive"] = True
                if worker.get("enabled", True):
                    self.save_state(state)
                    self.tick(force=False)
                else:
                    worker["last_status"] = "disabled"
                    self.save_state(state)
            except Exception as exc:
                state = self.load_state()
                worker = state.setdefault("worker", self._default_state()["worker"])
                worker["last_tick_at"] = self.now_iso_fn()
                worker["heartbeat_at"] = self.now_iso_fn()
                worker["last_status"] = "error"
                worker["last_error"] = str(exc)
                worker["failure_count"] = int(worker.get("failure_count") or 0) + 1
                self.append_event(state, "worker_error", None, {"error": str(exc)})
                self.save_state(state)
            finally:
                state = self.load_state()
                worker = state.setdefault("worker", self._default_state()["worker"])
                worker["heartbeat_at"] = self.now_iso_fn()
                worker["thread_alive"] = True
                worker["loop_lag_seconds"] = round(max(0.0, time.time() - started), 3)
                self.save_state(state)
                time.sleep(max(1, int(worker.get("poll_interval_seconds") or 1)))
