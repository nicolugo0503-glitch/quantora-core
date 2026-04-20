
# QNT30511 — Portfolio Reconciliation + Drift Detection

from datetime import datetime, timezone
from typing import Dict, Any, List

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30511ReconciliationEngine:
    def __init__(self, tolerance_pct: float = 2.0):
        self.tolerance_pct = tolerance_pct
        self.last_report = {}

    def reconcile(self, expected_positions: List[Dict], actual_positions: List[Dict]) -> Dict[str, Any]:
        expected_map = {p.get("symbol"): p for p in expected_positions}
        actual_map = {p.get("symbol"): p for p in actual_positions}

        all_symbols = set(expected_map.keys()) | set(actual_map.keys())

        rows = []
        drift_detected = False

        for sym in all_symbols:
            exp = expected_map.get(sym, {})
            act = actual_map.get(sym, {})

            exp_qty = float(exp.get("qty", 0))
            act_qty = float(act.get("qty", 0))

            diff = act_qty - exp_qty
            pct = 0.0
            if exp_qty != 0:
                pct = abs(diff / exp_qty) * 100

            drift = pct > self.tolerance_pct

            if drift:
                drift_detected = True

            rows.append({
                "symbol": sym,
                "expected_qty": exp_qty,
                "actual_qty": act_qty,
                "diff": diff,
                "diff_pct": round(pct, 4),
                "drift": drift
            })

        report = {
            "timestamp": _ts(),
            "drift_detected": drift_detected,
            "rows": rows
        }

        self.last_report = report
        return report

    def get_last_report(self):
        return self.last_report or {"timestamp": _ts(), "rows": []}
