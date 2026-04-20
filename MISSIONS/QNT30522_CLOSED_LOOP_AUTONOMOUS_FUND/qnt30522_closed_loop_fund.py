# QNT30522 — Closed-Loop Autonomous Fund

from datetime import datetime, timezone
from typing import Dict, Any, List

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30522ClosedLoopFund:
    def __init__(self, allocation_brain=None, adaptive_engine=None, broker_adapter=None):
        self.allocation_brain = allocation_brain
        self.adaptive_engine = adaptive_engine
        self.broker_adapter = broker_adapter
        self.cycles: List[Dict[str, Any]] = []

    def run_cycle(self, fund_id: str, capital: float, signals: Dict[str, float], pnl_by_asset: Dict[str, float], dry_run: bool = True):
        adaptive_updates = []
        if self.adaptive_engine is not None:
            for asset, pnl in pnl_by_asset.items():
                if hasattr(self.adaptive_engine, "update_performance"):
                    adaptive_updates.append(self.adaptive_engine.update_performance(asset, pnl))

        if self.adaptive_engine is not None and hasattr(self.adaptive_engine, "adaptive_allocate"):
            alloc_result = self.adaptive_engine.adaptive_allocate(capital)
            allocations = alloc_result.get("allocations", {})
        elif self.allocation_brain is not None and hasattr(self.allocation_brain, "allocate"):
            alloc_result = self.allocation_brain.allocate(fund_id, capital, signals)
            allocations = alloc_result.get("allocations", {})
        else:
            total = sum(max(v, 0) for v in signals.values()) or 1.0
            allocations = {k: round((max(v,0)/total)*capital,2) for k,v in signals.items()}
            alloc_result = {"allocations": allocations}

        orders = []
        for asset, amount in allocations.items():
            side = "buy" if amount > 0 else "hold"
            orders.append({
                "symbol": asset,
                "side": side,
                "notional": round(amount, 2),
                "source": "qnt30522_closed_loop"
            })

        execution_result = {
            "dry_run": dry_run,
            "submitted_orders": orders,
            "submitted_count": len(orders),
        }

        if not dry_run and self.broker_adapter is not None and hasattr(self.broker_adapter, "submit_order"):
            submitted = []
            for order in orders:
                try:
                    submitted.append(self.broker_adapter.submit_order(order))
                except Exception as e:
                    submitted.append({"error": str(e), "order": order})
            execution_result = {
                "dry_run": False,
                "submitted_orders": submitted,
                "submitted_count": len(submitted),
            }

        cycle = {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "capital": capital,
            "signals": signals,
            "pnl_by_asset": pnl_by_asset,
            "adaptive_updates": adaptive_updates,
            "allocations": allocations,
            "execution": execution_result,
        }
        self.cycles.append(cycle)
        self.cycles = self.cycles[-200:]
        return cycle

    def get_cycles(self):
        return self.cycles[-100:]
