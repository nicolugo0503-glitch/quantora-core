
from __future__ import annotations
from typing import Any, Dict
from backend.truth_engine import build_truth_snapshot
from backend.reconciliation_guard import evaluate_guard


class StabilitySyncEngine:
    def run(self, local_positions, broker_positions, account=None) -> Dict[str, Any]:
        truth = build_truth_snapshot(local_positions, broker_positions, account or {})
        guard = evaluate_guard(truth)
        return {
            'status': 'ok',
            'truth': truth,
            'guard': guard,
            'synced': guard.get('critical_count', 0) == 0,
        }
