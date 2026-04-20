from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'strategy_deployment_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50003',
        'status': 'degraded',
        'execution_mode': 'paper',
        'safe_mode': True,
        'current_regime': 'neutral',
        'liquidity_state': 'normal',
        'max_concurrent_strategies': 3,
        'max_strategy_weight': 0.40,
        'deployment_profiles': [
            {
                'strategy_id': 'alpha_trend',
                'name': 'Alpha Trend',
                'symbol': 'BTCUSDT',
                'asset_class': 'crypto',
                'preferred_regimes': ['bull', 'neutral'],
                'warmup_required': False,
                'deployment_readiness': 0.96,
                'max_live_weight': 0.36,
                'min_ticket_pct': 0.10,
                'allowed_brokers': ['binance', 'paper'],
                'status': 'standby',
                'enabled': True,
            },
            {
                'strategy_id': 'beta_mean_revert',
                'name': 'Beta Mean Revert',
                'symbol': 'ETHUSDT',
                'asset_class': 'crypto',
                'preferred_regimes': ['neutral', 'range'],
                'warmup_required': False,
                'deployment_readiness': 0.88,
                'max_live_weight': 0.28,
                'min_ticket_pct': 0.08,
                'allowed_brokers': ['binance', 'paper'],
                'status': 'standby',
                'enabled': True,
            },
            {
                'strategy_id': 'macro_defense',
                'name': 'Macro Defense',
                'symbol': 'USDTUSD',
                'asset_class': 'cash_overlay',
                'preferred_regimes': ['stress', 'bear', 'neutral'],
                'warmup_required': False,
                'deployment_readiness': 0.99,
                'max_live_weight': 0.42,
                'min_ticket_pct': 0.05,
                'allowed_brokers': ['ibkr', 'paper', 'binance'],
                'status': 'active',
                'enabled': True,
            },
        ],
        'current_plan': None,
        'active_deployments': [],
        'release_queue': [],
        'history': [],
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
        'event_id': f'strategy_deploy_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
