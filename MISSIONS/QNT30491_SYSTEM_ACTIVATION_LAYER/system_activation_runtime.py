# QNT30491 — SYSTEM ACTIVATION LAYER
# Additive mission module only. No core files modified.

import time
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List


@dataclass
class QuantoraState:
    active_fund: str = ""
    last_nav: Dict[str, Any] = field(default_factory=dict)
    last_positions: List[dict] = field(default_factory=list)
    last_dashboard: List[dict] = field(default_factory=list)
    last_fees: List[dict] = field(default_factory=list)
    timestamp: float = 0.0
    cycle_count: int = 0
    status: str = "idle"


class EventLog:
    def __init__(self):
        self.events: List[dict] = []

    def add(self, event_type: str, payload: Dict[str, Any]) -> None:
        self.events.append({
            "ts": time.time(),
            "event_type": event_type,
            "payload": payload,
        })

    def tail(self, n: int = 10) -> List[dict]:
        return self.events[-n:]


class SafetyController:
    def __init__(self):
        self.kill_switch = False
        self.paused = False
        self.max_drawdown_pct = None

    def set_kill_switch(self, value: bool) -> None:
        self.kill_switch = bool(value)

    def set_paused(self, value: bool) -> None:
        self.paused = bool(value)

    def set_max_drawdown_pct(self, value: float) -> None:
        self.max_drawdown_pct = float(value)

    def validate_cycle(self, nav_snapshot: Dict[str, Any], starting_nav: float) -> Dict[str, Any]:
        if self.kill_switch:
            return {"ok": False, "reason": "kill_switch_active"}

        if self.paused:
            return {"ok": False, "reason": "runtime_paused"}

        current_nav = float(nav_snapshot.get("nav", 0.0))
        if self.max_drawdown_pct is not None and starting_nav > 0:
            drawdown_pct = max(0.0, (starting_nav - current_nav) / starting_nav * 100.0)
            if drawdown_pct > self.max_drawdown_pct:
                return {
                    "ok": False,
                    "reason": "max_drawdown_exceeded",
                    "drawdown_pct": round(drawdown_pct, 4),
                }

        return {"ok": True}


class QuantoraRuntimeEngine:
    def __init__(self, live_bridge, integration_engine):
        self.live_bridge = live_bridge
        self.integration_engine = integration_engine
        self.state = QuantoraState()
        self.log = EventLog()
        self.safety = SafetyController()

    def run_cycle(
        self,
        fund_id: str,
        capital: float,
        broker_positions: List[dict],
        broker_orders: List[dict],
        cash: float,
        liabilities: float = 0.0,
        total_shares: float = 1.0,
        starting_nav: float = 0.0,
        net_profit: float = 0.0,
    ) -> Dict[str, Any]:
        self.log.add("cycle_started", {"fund_id": fund_id, "capital": capital})

        result = self.live_bridge.sync_into_integration_cycle(
            integration_engine=self.integration_engine,
            fund_id=fund_id,
            capital=capital,
            broker_positions=broker_positions,
            broker_orders=broker_orders,
            cash=cash,
            liabilities=liabilities,
            total_shares=total_shares,
            starting_nav=starting_nav,
            net_profit=net_profit,
        )

        nav_snapshot = result.get("nav_snapshot", {})
        safety_check = self.safety.validate_cycle(nav_snapshot, starting_nav=starting_nav)

        if not safety_check.get("ok", False):
            self.state.status = "stopped"
            self.state.timestamp = time.time()
            self.log.add("cycle_blocked", safety_check)
            return {
                "status": "blocked",
                "reason": safety_check.get("reason"),
                "details": safety_check,
                "state": asdict(self.state),
            }

        execution_snapshot = result.get("execution_snapshot", {})
        self.state.active_fund = fund_id
        self.state.last_nav = nav_snapshot
        self.state.last_positions = execution_snapshot.get("positions", [])
        self.state.last_dashboard = result.get("dashboard", [])
        self.state.last_fees = result.get("fees", [])
        self.state.timestamp = time.time()
        self.state.cycle_count += 1
        self.state.status = "running"

        self.log.add("cycle_completed", {
            "fund_id": fund_id,
            "nav": nav_snapshot.get("nav", 0.0),
            "cycle_count": self.state.cycle_count,
        })

        return {
            "status": "ok",
            "cycle_count": self.state.cycle_count,
            "result": result,
            "state": asdict(self.state),
            "event_log_tail": self.log.tail(),
        }

    def run_simulation(
        self,
        cycles: int,
        interval_seconds: float,
        fund_id: str,
        capital: float,
        broker_positions: List[dict],
        broker_orders: List[dict],
        cash: float,
        liabilities: float = 0.0,
        total_shares: float = 1.0,
        starting_nav: float = 0.0,
        net_profit: float = 0.0,
    ) -> List[dict]:
        outputs: List[dict] = []
        for _ in range(int(cycles)):
            cycle_output = self.run_cycle(
                fund_id=fund_id,
                capital=capital,
                broker_positions=broker_positions,
                broker_orders=broker_orders,
                cash=cash,
                liabilities=liabilities,
                total_shares=total_shares,
                starting_nav=starting_nav,
                net_profit=net_profit,
            )
            outputs.append(cycle_output)
            if cycle_output.get("status") != "ok":
                break
            if interval_seconds > 0:
                time.sleep(interval_seconds)
        return outputs
