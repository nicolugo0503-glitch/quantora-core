# QNT30534 — Performance + PnL Engine

from datetime import datetime, timezone
from typing import Dict, Any, List

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30534PerformanceEngine:
    def __init__(self):
        self.initial_nav = 100000.0
        self.current_nav = 100000.0
        self.high_water_mark = 100000.0
        self.position_pnl: Dict[str, float] = {}
        self.strategy_pnl: Dict[str, float] = {}
        self.snapshots: List[Dict[str, Any]] = []

    def record_cycle(self, positions: Dict[str, float] = None, strategy_id: str = "core", realized_pnl: float = 0.0, unrealized_pnl: float = 0.0) -> Dict[str, Any]:
        positions = positions or {}
        cycle_total = float(realized_pnl) + float(unrealized_pnl)

        for symbol, pnl in positions.items():
            self.position_pnl[symbol] = round(self.position_pnl.get(symbol, 0.0) + float(pnl), 4)

        self.strategy_pnl[strategy_id] = round(self.strategy_pnl.get(strategy_id, 0.0) + cycle_total, 4)
        self.current_nav = round(self.current_nav + cycle_total, 4)
        self.high_water_mark = max(self.high_water_mark, self.current_nav)

        drawdown_pct = 0.0
        if self.high_water_mark > 0:
            drawdown_pct = round(((self.current_nav - self.high_water_mark) / self.high_water_mark) * 100.0, 4)

        snapshot = {
            "timestamp": _ts(),
            "strategy_id": strategy_id,
            "realized_pnl": round(float(realized_pnl), 4),
            "unrealized_pnl": round(float(unrealized_pnl), 4),
            "cycle_total_pnl": round(cycle_total, 4),
            "nav": round(self.current_nav, 4),
            "total_pnl": round(self.current_nav - self.initial_nav, 4),
            "drawdown_pct": drawdown_pct,
            "win_rate": self._compute_win_rate(cycle_total),
            "position_pnl": dict(self.position_pnl),
            "strategy_pnl": dict(self.strategy_pnl),
        }
        self.snapshots.append(snapshot)
        self.snapshots = self.snapshots[-500:]
        return snapshot

    def _compute_win_rate(self, latest_cycle_total: float = 0.0) -> float:
        hypothetical = list(self.snapshots)
        if latest_cycle_total != 0.0:
            hypothetical = hypothetical + [{"cycle_total_pnl": latest_cycle_total}]
        if not hypothetical:
            return 0.0
        wins = sum(1 for s in hypothetical if float(s.get("cycle_total_pnl", 0.0)) > 0)
        return round(wins / max(len(hypothetical), 1), 4)

    def summary(self) -> Dict[str, Any]:
        drawdown_pct = 0.0
        if self.high_water_mark > 0:
            drawdown_pct = round(((self.current_nav - self.high_water_mark) / self.high_water_mark) * 100.0, 4)
        return {
            "timestamp": _ts(),
            "initial_nav": round(self.initial_nav, 4),
            "nav": round(self.current_nav, 4),
            "total_pnl": round(self.current_nav - self.initial_nav, 4),
            "drawdown_pct": drawdown_pct,
            "win_rate": self._compute_win_rate(),
            "position_pnl": dict(self.position_pnl),
            "strategy_pnl": dict(self.strategy_pnl),
            "snapshot_count": len(self.snapshots),
        }

    def history(self) -> List[Dict[str, Any]]:
        return self.snapshots[-100:]
