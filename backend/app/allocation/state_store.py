from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'allocation_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50002',
        'status': 'degraded',
        'execution_mode': 'paper',
        'safe_mode': True,
        'total_capital': 1000000.0,
        'reserve_target_weight': 0.10,
        'max_strategy_weight': 0.35,
        'max_regime_shift_pct': 0.15,
        'last_regime': 'neutral',
        'strategies': [
            {
                'strategy_id': 'alpha_trend',
                'name': 'Alpha Trend',
                'symbol': 'BTCUSDT',
                'asset_class': 'crypto',
                'signal_strength': 0.82,
                'conviction': 0.76,
                'liquidity_score': 0.91,
                'risk_budget': 0.24,
                'drawdown_pct': 0.03,
                'max_drawdown_limit': 0.12,
                'preferred_regimes': ['bull', 'neutral'],
                'enabled': True,
            },
            {
                'strategy_id': 'beta_mean_revert',
                'name': 'Beta Mean Revert',
                'symbol': 'ETHUSDT',
                'asset_class': 'crypto',
                'signal_strength': 0.68,
                'conviction': 0.63,
                'liquidity_score': 0.88,
                'risk_budget': 0.18,
                'drawdown_pct': 0.04,
                'max_drawdown_limit': 0.10,
                'preferred_regimes': ['neutral', 'range'],
                'enabled': True,
            },
            {
                'strategy_id': 'macro_defense',
                'name': 'Macro Defense',
                'symbol': 'USDTUSD',
                'asset_class': 'cash_overlay',
                'signal_strength': 0.51,
                'conviction': 0.90,
                'liquidity_score': 1.00,
                'risk_budget': 0.30,
                'drawdown_pct': 0.01,
                'max_drawdown_limit': 0.06,
                'preferred_regimes': ['stress', 'bear', 'neutral'],
                'enabled': True,
            },
        ],
        'latest_plan': None,
        'history': [],
        'committee_log': [],
        'rebalance_preview': None,
        'export_queue': [],
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
        'event_id': f'allocation_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
