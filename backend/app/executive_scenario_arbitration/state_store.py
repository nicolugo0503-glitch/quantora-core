from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'executive_scenario_arbitration_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50024',
        'status': 'degraded',
        'policy': {
            'enabled': True,
            'auto_sync_sources': True,
            'require_committee_context': True,
            'require_risk_clearance': True,
            'require_safe_mode_for_live_override': True,
            'require_policy_alignment': True,
            'minimum_policy_alignment_score': 85.0,
            'minimum_scenario_resilience_score': 78.0,
            'minimum_available_liquidity': 100000.0,
            'max_capital_delta_pct': 0.12,
            'max_live_notional_without_override': 250000.0,
            'max_scenarios_to_keep': 300,
            'max_decisions_to_keep': 300,
        },
        'last_sync': None,
        'sync_history': [],
        'allocation_policies': [],
        'scenario_cases': [],
        'arbitration_decisions': [],
        'audit_log': [],
    }


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return default_state()
    return json.loads(STATE_PATH.read_text(encoding='utf-8'))


def save_state(state: Dict[str, Any]) -> Dict[str, Any]:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')
    return state


def append_audit(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    state.setdefault('audit_log', []).insert(0, {
        'event_id': f'executive_scenario_arbitration_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
