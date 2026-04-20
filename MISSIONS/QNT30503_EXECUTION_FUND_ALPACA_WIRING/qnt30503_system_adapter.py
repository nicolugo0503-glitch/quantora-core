# QNT30503 — Execution / Fund / Alpaca Wiring Adapter
# Additive mission module only. No existing core files modified.
#
# PURPOSE
# Replace the QNT30502 default in-memory state model with an adapter that can read
# from existing execution, fund, investor, NAV, and Alpaca-connected system components.

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30503SystemAdapter:
    def __init__(
        self,
        execution_bridge: Any = None,
        fund_engine: Any = None,
        nav_engine: Any = None,
        investor_dashboard_engine: Any = None,
        monetization_engine: Any = None,
        alpaca_client: Any = None,
        runtime_engine: Any = None,
    ) -> None:
        self.execution_bridge = execution_bridge
        self.fund_engine = fund_engine
        self.nav_engine = nav_engine
        self.investor_dashboard_engine = investor_dashboard_engine
        self.monetization_engine = monetization_engine
        self.alpaca_client = alpaca_client
        self.runtime_engine = runtime_engine

        self.runtime_control_state: Dict[str, Any] = {
            "status": "wired-fallback",
            "cycle_count": 0,
            "nav": 0.0,
            "active_fund": "FUND1",
            "pnl": 0.0,
            "kill_switch": False,
            "paused": False,
            "last_updated": _utc_now(),
        }

    # -------------------------
    # Safe source readers
    # -------------------------
    def _read_runtime_state(self) -> Dict[str, Any]:
        if self.runtime_engine and hasattr(self.runtime_engine, "state"):
            state = getattr(self.runtime_engine, "state")
            return {
                "status": getattr(state, "status", "unknown"),
                "cycle_count": getattr(state, "cycle_count", 0),
                "nav": float(getattr(state, "last_nav", {}).get("nav", 0.0)) if isinstance(getattr(state, "last_nav", {}), dict) else 0.0,
                "active_fund": getattr(state, "active_fund", "FUND1"),
                "pnl": float(getattr(state, "last_nav", {}).get("total_pnl", 0.0)) if isinstance(getattr(state, "last_nav", {}), dict) else 0.0,
                "kill_switch": bool(getattr(getattr(self.runtime_engine, "safety", None), "kill_switch", False)),
                "paused": bool(getattr(getattr(self.runtime_engine, "safety", None), "paused", False)),
                "last_updated": _utc_now(),
            }
        return dict(self.runtime_control_state)

    def _read_alpaca_positions(self) -> List[Dict[str, Any]]:
        if self.alpaca_client and hasattr(self.alpaca_client, "get_all_positions"):
            try:
                rows = self.alpaca_client.get_all_positions()
                return list(rows or [])
            except Exception:
                return []
        return []

    def _read_alpaca_orders(self) -> List[Dict[str, Any]]:
        if self.alpaca_client and hasattr(self.alpaca_client, "get_open_orders"):
            try:
                rows = self.alpaca_client.get_open_orders()
                return list(rows or [])
            except Exception:
                return []
        return []

    def _read_fund_rows(self) -> List[Dict[str, Any]]:
        runtime = self._read_runtime_state()
        fund_id = runtime.get("active_fund", "FUND1")

        if self.execution_bridge and hasattr(self.execution_bridge, "build_execution_sync_packet"):
            try:
                packet = self.execution_bridge.build_execution_sync_packet(
                    order_rows=self._read_alpaca_orders(),
                    position_rows=self._read_alpaca_positions(),
                    fill_rows=[],
                )
                exposure_summary = packet.get("exposure_summary", [])
                if exposure_summary:
                    rows = []
                    for row in exposure_summary:
                        rows.append({
                            "sleeve": row.get("fund_id", "UNKNOWN_FUND"),
                            "capital": float(row.get("market_value", 0.0)),
                        })
                    return rows
            except Exception:
                pass

        if self.fund_engine and hasattr(self.fund_engine, "allocate"):
            try:
                allocation = self.fund_engine.allocate(fund_id, 1000000.0)
                return [{"sleeve": k, "capital": float(v)} for k, v in allocation.items()]
            except Exception:
                pass

        return [
            {"sleeve": "Crypto Momentum", "capital": 500000.0},
            {"sleeve": "Low Risk Yield", "capital": 300000.0},
            {"sleeve": "AI Signals", "capital": 200000.0},
        ]

    def _read_investor_rows(self) -> List[Dict[str, Any]]:
        if self.investor_dashboard_engine and hasattr(self.investor_dashboard_engine, "build_dashboard_rows"):
            try:
                rows = self.investor_dashboard_engine.build_dashboard_rows()
                normalized = []
                for row in rows:
                    normalized.append({
                        "investor": row.get("investor_name", row.get("investor_id", "Unknown Investor")),
                        "fund": row.get("fund_id", "FUND1"),
                        "market_value": float(row.get("market_value", 0.0)),
                        "ownership_pct": float(row.get("ownership_pct", 0.0)),
                    })
                if normalized:
                    return normalized
            except Exception:
                pass

        return [
            {"investor": "Nicolas Capital", "fund": "FUND1", "market_value": 432000.0, "ownership_pct": 60.0},
            {"investor": "Atlas Growth", "fund": "FUND1", "market_value": 288000.0, "ownership_pct": 40.0},
        ]

    def _read_exposure_summary(self) -> Dict[str, Any]:
        positions = self._read_alpaca_positions()
        pnl = 0.0
        market_value = 0.0
        for row in positions:
            market_value += float(row.get("market_value", 0.0))
            pnl += float(row.get("unrealized_pnl", 0.0)) + float(row.get("realized_pnl", 0.0))

        if market_value > 0:
            return {
                "pnl": round(pnl, 2),
                "market_value": round(market_value, 2),
                "source": "alpaca-or-live-positions",
                "last_updated": _utc_now(),
            }

        runtime = self._read_runtime_state()
        return {
            "pnl": float(runtime.get("pnl", 0.0)),
            "market_value": 0.0,
            "source": "runtime-or-fallback",
            "last_updated": _utc_now(),
        }

    def _read_nav(self) -> float:
        runtime = self._read_runtime_state()
        if float(runtime.get("nav", 0.0)) > 0:
            return float(runtime["nav"])

        if self.nav_engine and hasattr(self.nav_engine, "snapshot_dict"):
            try:
                fund_id = runtime.get("active_fund", "FUND1")
                snap = self.nav_engine.snapshot_dict(fund_id)
                return float(snap.get("nav", 0.0))
            except Exception:
                return 0.0
        return 0.0

    # -------------------------
    # Public contract methods for QNT30502 router
    # -------------------------
    def get_runtime_state(self) -> Dict[str, Any]:
        runtime = self._read_runtime_state()
        runtime["nav"] = self._read_nav() or runtime.get("nav", 0.0)
        runtime["last_updated"] = _utc_now()
        return runtime

    def get_fund_summary(self) -> Dict[str, Any]:
        return {
            "sleeves": self._read_fund_rows(),
            "last_updated": _utc_now(),
        }

    def get_investor_overview(self) -> Dict[str, Any]:
        return {
            "rows": self._read_investor_rows(),
            "last_updated": _utc_now(),
        }

    def get_exposure_summary(self) -> Dict[str, Any]:
        return self._read_exposure_summary()

    def apply_action(self, action: str) -> Dict[str, Any]:
        action = str(action).lower().strip()

        if self.runtime_engine and hasattr(self.runtime_engine, "safety"):
            safety = getattr(self.runtime_engine, "safety")
            if action == "start":
                if hasattr(safety, "set_kill_switch"):
                    safety.set_kill_switch(False)
                if hasattr(safety, "set_paused"):
                    safety.set_paused(False)
                self.runtime_control_state["status"] = "running"
            elif action == "pause":
                if hasattr(safety, "set_paused"):
                    safety.set_paused(True)
                self.runtime_control_state["status"] = "paused"
            elif action == "resume":
                if hasattr(safety, "set_paused"):
                    safety.set_paused(False)
                if hasattr(safety, "set_kill_switch"):
                    safety.set_kill_switch(False)
                self.runtime_control_state["status"] = "running"
            elif action == "kill":
                if hasattr(safety, "set_kill_switch"):
                    safety.set_kill_switch(True)
                if hasattr(safety, "set_paused"):
                    safety.set_paused(False)
                self.runtime_control_state["status"] = "killed"
        else:
            if action == "start":
                self.runtime_control_state["status"] = "running"
                self.runtime_control_state["paused"] = False
                self.runtime_control_state["kill_switch"] = False
                self.runtime_control_state["cycle_count"] += 1
            elif action == "pause":
                self.runtime_control_state["status"] = "paused"
                self.runtime_control_state["paused"] = True
            elif action == "resume":
                self.runtime_control_state["status"] = "running"
                self.runtime_control_state["paused"] = False
                self.runtime_control_state["kill_switch"] = False
                self.runtime_control_state["cycle_count"] += 1
            elif action == "kill":
                self.runtime_control_state["status"] = "killed"
                self.runtime_control_state["kill_switch"] = True
                self.runtime_control_state["paused"] = False

        self.runtime_control_state["last_updated"] = _utc_now()
        return {
            "ok": True,
            "action": action,
            "runtime": self.get_runtime_state(),
        }
