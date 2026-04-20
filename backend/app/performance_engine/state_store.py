from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'performance_engine_state.json'


def _seed_nav_series() -> List[Dict[str, Any]]:
    today = date.today()
    days = [today - timedelta(days=4), today - timedelta(days=3), today - timedelta(days=2), today - timedelta(days=1), today]
    return [
        {
            'as_of_date': days[0].isoformat(),
            'equity': 1000000.0,
            'nav_per_unit': 100.0,
            'net_flow': 0.0,
            'gross_exposure_pct': 0.32,
            'net_exposure_pct': 0.18,
            'cash_pct': 0.68,
            'strategy_attribution': [
                {'strategy_id': 'alpha_trend', 'pnl': 0.0, 'return_contribution_pct': 0.0, 'gross_exposure_pct': 0.12},
                {'strategy_id': 'beta_mean_revert', 'pnl': 0.0, 'return_contribution_pct': 0.0, 'gross_exposure_pct': 0.10},
                {'strategy_id': 'macro_defense', 'pnl': 0.0, 'return_contribution_pct': 0.0, 'gross_exposure_pct': 0.10},
            ],
        },
        {
            'as_of_date': days[1].isoformat(),
            'equity': 1016000.0,
            'nav_per_unit': 101.6,
            'net_flow': 0.0,
            'gross_exposure_pct': 0.36,
            'net_exposure_pct': 0.22,
            'cash_pct': 0.64,
            'strategy_attribution': [
                {'strategy_id': 'alpha_trend', 'pnl': 9000.0, 'return_contribution_pct': 0.009, 'gross_exposure_pct': 0.15},
                {'strategy_id': 'beta_mean_revert', 'pnl': 4000.0, 'return_contribution_pct': 0.004, 'gross_exposure_pct': 0.11},
                {'strategy_id': 'macro_defense', 'pnl': 3000.0, 'return_contribution_pct': 0.003, 'gross_exposure_pct': 0.10},
            ],
        },
        {
            'as_of_date': days[2].isoformat(),
            'equity': 1009000.0,
            'nav_per_unit': 100.9,
            'net_flow': 0.0,
            'gross_exposure_pct': 0.34,
            'net_exposure_pct': 0.16,
            'cash_pct': 0.66,
            'strategy_attribution': [
                {'strategy_id': 'alpha_trend', 'pnl': -7000.0, 'return_contribution_pct': -0.007, 'gross_exposure_pct': 0.13},
                {'strategy_id': 'beta_mean_revert', 'pnl': 1000.0, 'return_contribution_pct': 0.001, 'gross_exposure_pct': 0.11},
                {'strategy_id': 'macro_defense', 'pnl': -1000.0, 'return_contribution_pct': -0.001, 'gross_exposure_pct': 0.10},
            ],
        },
        {
            'as_of_date': days[3].isoformat(),
            'equity': 1034000.0,
            'nav_per_unit': 103.4,
            'net_flow': 0.0,
            'gross_exposure_pct': 0.39,
            'net_exposure_pct': 0.24,
            'cash_pct': 0.61,
            'strategy_attribution': [
                {'strategy_id': 'alpha_trend', 'pnl': 13000.0, 'return_contribution_pct': 0.013, 'gross_exposure_pct': 0.17},
                {'strategy_id': 'beta_mean_revert', 'pnl': 7000.0, 'return_contribution_pct': 0.007, 'gross_exposure_pct': 0.12},
                {'strategy_id': 'macro_defense', 'pnl': 5000.0, 'return_contribution_pct': 0.005, 'gross_exposure_pct': 0.10},
            ],
        },
        {
            'as_of_date': days[4].isoformat(),
            'equity': 1027000.0,
            'nav_per_unit': 102.7,
            'net_flow': 0.0,
            'gross_exposure_pct': 0.37,
            'net_exposure_pct': 0.20,
            'cash_pct': 0.63,
            'strategy_attribution': [
                {'strategy_id': 'alpha_trend', 'pnl': -4000.0, 'return_contribution_pct': -0.004, 'gross_exposure_pct': 0.15},
                {'strategy_id': 'beta_mean_revert', 'pnl': -2000.0, 'return_contribution_pct': -0.002, 'gross_exposure_pct': 0.12},
                {'strategy_id': 'macro_defense', 'pnl': -1000.0, 'return_contribution_pct': -0.001, 'gross_exposure_pct': 0.10},
            ],
        },
    ]


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50005',
        'status': 'degraded',
        'config': {
            'benchmark_rate_annual': 0.02,
            'minimum_acceptable_return_annual': 0.0,
            'target_volatility_annual': 0.12,
            'trading_days_annual': 252,
        },
        'nav_series': _seed_nav_series(),
        'metrics': {},
        'investor_metrics': {},
        'strategy_attribution': [],
        'recompute_log': [],
        'audit_log': [],
        'latest_recompute_at': None,
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
        'event_id': f'performance_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
