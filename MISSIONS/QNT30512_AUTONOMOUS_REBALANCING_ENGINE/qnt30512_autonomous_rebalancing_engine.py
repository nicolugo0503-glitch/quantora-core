# QNT30512 — Autonomous Rebalancing Engine
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Dict, Any, List


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30512AutonomousRebalancingEngine:
    def __init__(self, drift_tolerance_pct: float = 2.0):
        self.drift_tolerance_pct = float(drift_tolerance_pct)
        self.last_plan: Dict[str, Any] = {}

    def build_rebalance_plan(
        self,
        target_positions: List[Dict[str, Any]],
        actual_positions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        target_map = {str(p.get("symbol")): p for p in target_positions}
        actual_map = {str(p.get("symbol")): p for p in actual_positions}
        all_symbols = sorted(set(target_map.keys()) | set(actual_map.keys()))

        orders: List[Dict[str, Any]] = []
        rows: List[Dict[str, Any]] = []

        for symbol in all_symbols:
            target = target_map.get(symbol, {})
            actual = actual_map.get(symbol, {})

            target_qty = float(target.get("qty", 0.0))
            actual_qty = float(actual.get("qty", 0.0))
            diff_qty = round(target_qty - actual_qty, 8)

            diff_pct = 0.0
            if target_qty != 0:
                diff_pct = abs(diff_qty / target_qty) * 100.0

            needs_rebalance = abs(diff_qty) > 0 and diff_pct > self.drift_tolerance_pct

            row = {
                "symbol": symbol,
                "target_qty": target_qty,
                "actual_qty": actual_qty,
                "diff_qty": diff_qty,
                "diff_pct": round(diff_pct, 4),
                "needs_rebalance": needs_rebalance,
            }
            rows.append(row)

            if needs_rebalance:
                side = "buy" if diff_qty > 0 else "sell"
                orders.append({
                    "symbol": symbol,
                    "side": side,
                    "qty": abs(diff_qty),
                    "source": "qnt30512_rebalance_plan",
                })

        plan = {
            "timestamp": _ts(),
            "drift_tolerance_pct": self.drift_tolerance_pct,
            "rows": rows,
            "orders": orders,
            "rebalance_required": len(orders) > 0,
            "order_count": len(orders),
        }
        self.last_plan = plan
        return plan

    def get_last_plan(self) -> Dict[str, Any]:
        return self.last_plan or {
            "timestamp": _ts(),
            "drift_tolerance_pct": self.drift_tolerance_pct,
            "rows": [],
            "orders": [],
            "rebalance_required": False,
            "order_count": 0,
        }


class QNT30512RebalanceExecutionAdapter:
    def __init__(self, engine: QNT30512AutonomousRebalancingEngine, broker_adapter: Any = None):
        self.engine = engine
        self.broker_adapter = broker_adapter
        self.last_execution: Dict[str, Any] = {}

    def execute_last_plan(self, dry_run: bool = True) -> Dict[str, Any]:
        plan = self.engine.get_last_plan()
        orders = plan.get("orders", [])

        if dry_run or self.broker_adapter is None:
            result = {
                "timestamp": _ts(),
                "dry_run": True,
                "submitted_orders": orders,
                "submitted_count": len(orders),
            }
            self.last_execution = result
            return result

        submitted = []
        for order in orders:
            if hasattr(self.broker_adapter, "submit_order"):
                try:
                    submitted.append(self.broker_adapter.submit_order(order))
                except Exception as e:
                    submitted.append({"error": str(e), "order": order})

        result = {
            "timestamp": _ts(),
            "dry_run": False,
            "submitted_orders": submitted,
            "submitted_count": len(submitted),
        }
        self.last_execution = result
        return result

    def get_last_execution(self) -> Dict[str, Any]:
        return self.last_execution or {
            "timestamp": _ts(),
            "dry_run": True,
            "submitted_orders": [],
            "submitted_count": 0,
        }
