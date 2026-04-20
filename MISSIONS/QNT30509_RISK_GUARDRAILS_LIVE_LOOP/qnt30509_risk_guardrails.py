# QNT30509 — Risk Guardrails in Live Loop
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30509RiskGuardrails:
    def __init__(
        self,
        max_notional_exposure: float = 1_000_000.0,
        max_drawdown_pct: float = 25.0,
        max_position_count: int = 50,
        blocked_symbols: Optional[List[str]] = None,
    ) -> None:
        self.max_notional_exposure = float(max_notional_exposure)
        self.max_drawdown_pct = float(max_drawdown_pct)
        self.max_position_count = int(max_position_count)
        self.blocked_symbols = set(blocked_symbols or [])
        self.last_report: Dict[str, Any] = {}

    def evaluate(
        self,
        runtime_state: Optional[Dict[str, Any]] = None,
        exposure_summary: Optional[Dict[str, Any]] = None,
        positions_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        runtime_state = runtime_state or {}
        exposure_summary = exposure_summary or {}
        positions_snapshot = positions_snapshot or {"positions": []}

        nav = float(runtime_state.get("nav", 0.0) or 0.0)
        pnl = float(exposure_summary.get("pnl", runtime_state.get("pnl", 0.0)) or 0.0)
        market_value = float(exposure_summary.get("market_value", 0.0) or 0.0)
        positions = positions_snapshot.get("positions", []) or []

        blocked_hits = [p for p in positions if str(p.get("symbol", "")) in self.blocked_symbols]
        drawdown_pct = 0.0
        if nav > 0 and pnl < 0:
            drawdown_pct = abs(pnl) / nav * 100.0

        breaches = {
            "max_notional_exposure_breached": market_value > self.max_notional_exposure,
            "max_drawdown_breached": drawdown_pct > self.max_drawdown_pct,
            "max_position_count_breached": len(positions) > self.max_position_count,
            "blocked_symbol_breached": len(blocked_hits) > 0,
        }

        severity = "ok"
        if any(breaches.values()):
            severity = "critical"

        report = {
            "timestamp": _utc_now(),
            "severity": severity,
            "breaches": breaches,
            "metrics": {
                "nav": round(nav, 2),
                "pnl": round(pnl, 2),
                "market_value": round(market_value, 2),
                "position_count": len(positions),
                "drawdown_pct": round(drawdown_pct, 4),
            },
            "blocked_symbol_hits": blocked_hits,
            "allow_loop_to_run": not any(breaches.values()),
        }
        self.last_report = report
        return report

    def get_last_report(self) -> Dict[str, Any]:
        return self.last_report or {
            "timestamp": _utc_now(),
            "severity": "unknown",
            "breaches": {},
            "metrics": {},
            "blocked_symbol_hits": [],
            "allow_loop_to_run": True,
        }


class QNT30509GuardedSchedulerAdapter:
    def __init__(
        self,
        scheduler: Any,
        guardrails: QNT30509RiskGuardrails,
        runtime_state_reader: Any = None,
        exposure_reader: Any = None,
        positions_reader: Any = None,
    ) -> None:
        self.scheduler = scheduler
        self.guardrails = guardrails
        self.runtime_state_reader = runtime_state_reader
        self.exposure_reader = exposure_reader
        self.positions_reader = positions_reader

    def _read_runtime(self) -> Dict[str, Any]:
        if callable(self.runtime_state_reader):
            try:
                return self.runtime_state_reader() or {}
            except Exception:
                return {}
        if hasattr(self.scheduler, "get_state"):
            try:
                state = self.scheduler.get_state() or {}
                last_result = state.get("last_result", {}) or {}
                runtime = last_result.get("runtime", {}) or {}
                runtime.setdefault("nav", runtime.get("nav", 0.0))
                return runtime
            except Exception:
                return {}
        return {}

    def _read_exposure(self) -> Dict[str, Any]:
        if callable(self.exposure_reader):
            try:
                return self.exposure_reader() or {}
            except Exception:
                return {}
        if hasattr(self.scheduler, "get_state"):
            try:
                state = self.scheduler.get_state() or {}
                last_result = state.get("last_result", {}) or {}
                return last_result.get("exposure", {}) or {}
            except Exception:
                return {}
        return {}

    def _read_positions(self) -> Dict[str, Any]:
        if callable(self.positions_reader):
            try:
                return self.positions_reader() or {"positions": []}
            except Exception:
                return {"positions": []}
        return {"positions": []}

    def _check(self) -> Dict[str, Any]:
        return self.guardrails.evaluate(
            runtime_state=self._read_runtime(),
            exposure_summary=self._read_exposure(),
            positions_snapshot=self._read_positions(),
        )

    def start(self) -> Dict[str, Any]:
        report = self._check()
        if not report["allow_loop_to_run"]:
            return {"ok": False, "status": "blocked_by_risk", "risk_report": report}
        return self.scheduler.start()

    def pause(self) -> Dict[str, Any]:
        return self.scheduler.pause()

    def resume(self) -> Dict[str, Any]:
        report = self._check()
        if not report["allow_loop_to_run"]:
            return {"ok": False, "status": "blocked_by_risk", "risk_report": report}
        return self.scheduler.resume()

    def kill(self) -> Dict[str, Any]:
        return self.scheduler.kill()

    def set_interval(self, seconds: float) -> Dict[str, Any]:
        return self.scheduler.set_interval(seconds)

    def get_state(self) -> Dict[str, Any]:
        state = self.scheduler.get_state()
        state["risk_report"] = self._check()
        return state
