
from __future__ import annotations
from typing import Any, Dict


def evaluate_guard(truth_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    mismatches = truth_snapshot.get('mismatches', []) or []
    critical = [m for m in mismatches if (m.get('severity') or '').lower() == 'critical']
    warns = [m for m in mismatches if (m.get('severity') or '').lower() != 'critical']
    if critical:
        status = 'BLOCK_NEW_TRADES'
        reason = 'Critical broker/local mismatch detected'
    elif warns:
        status = 'WARN'
        reason = 'Non-critical drift detected'
    else:
        status = 'ALIGNED'
        reason = 'Broker and Quantora are aligned'
    return {
        'status': status,
        'reason': reason,
        'critical_count': len(critical),
        'warning_count': len(warns),
        'block_new_trades': bool(critical),
    }
