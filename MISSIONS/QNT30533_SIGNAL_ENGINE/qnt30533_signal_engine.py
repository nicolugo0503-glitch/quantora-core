# QNT30533 — Signal Engine

from datetime import datetime, timezone
from typing import Dict, Any, List
import random

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30533SignalEngine:
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.last_signal: Dict[str, Any] = {}

    def generate_signals(self, prices: Dict[str, List[float]] = None, universe: List[str] = None) -> Dict[str, Any]:
        prices = prices or {}
        universe = universe or ["BTCUSD", "ETHUSD", "SOLUSD"]

        signals: Dict[str, float] = {}
        diagnostics: Dict[str, Any] = {}

        for symbol in universe:
            series = prices.get(symbol, []) or []

            if len(series) >= 3:
                recent = float(series[-1])
                baseline = sum(float(x) for x in series[-3:]) / 3.0
                score = 0.0 if baseline == 0 else (recent - baseline) / baseline
                score = max(min(score, 1.0), -1.0)
                signals[symbol] = round(max(score, 0.0), 4)
                diagnostics[symbol] = {
                    "mode": "momentum",
                    "recent": recent,
                    "baseline": round(baseline, 6),
                    "raw_score": round(score, 6),
                }
            else:
                fallback = round(random.uniform(0.05, 0.95), 4)
                signals[symbol] = fallback
                diagnostics[symbol] = {
                    "mode": "fallback_random",
                    "raw_score": fallback,
                }

        positive_total = sum(max(v, 0.0) for v in signals.values()) or 1.0
        normalized = {k: round(max(v, 0.0) / positive_total, 4) for k, v in signals.items()}

        payload = {
            "timestamp": _ts(),
            "universe": universe,
            "signals": normalized,
            "diagnostics": diagnostics,
        }
        self.last_signal = payload
        self.history.append(payload)
        self.history = self.history[-200:]
        return payload

    def build_tick_payload(
        self,
        fund_id: str = "FUND1",
        capital: float = 100000.0,
        prices: Dict[str, List[float]] = None,
        universe: List[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        sig = self.generate_signals(prices=prices, universe=universe)
        return {
            "payload": {
                "fund_id": fund_id,
                "capital": float(capital),
                "signals": sig["signals"],
                "pnl_by_asset": {symbol: 0.0 for symbol in sig["signals"].keys()},
                "dry_run": bool(dry_run),
            },
            "signal_snapshot": sig,
        }

    def get_last_signal(self) -> Dict[str, Any]:
        return self.last_signal or {
            "timestamp": _ts(),
            "universe": [],
            "signals": {},
            "diagnostics": {},
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history[-100:]
