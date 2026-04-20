import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix='/operator', tags=['operator-cockpit'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
ARTIFACTS_DIR = ROOT / 'backend' / 'artifacts'

EXECUTION_FILE = STATE_DIR / 'execution_state.json'
RISK_FILE = STATE_DIR / 'risk_kill_switch_state.json'
STRATEGY_FILE = STATE_DIR / 'strategy_deployment_state.json'
PERFORMANCE_FILE = STATE_DIR / 'performance_engine_state.json'
AUTONOMOUS_FILE = STATE_DIR / 'autonomous_execution_state.json'
LEDGER_FILE = ARTIFACTS_DIR / 'capital_ledger.json'
BROKER_TRUTH_FILE = STATE_DIR / 'live_broker_truth_state.json'
SYNC_FILE = STATE_DIR / 'real_position_fill_broker_sync_state.json'
PNL_TRUTH_FILE = STATE_DIR / 'real_pnl_equity_exposure_truth_state.json'
ORDER_ENTRY_FILE = STATE_DIR / 'real_order_entry_surface_state.json'
CREDENTIAL_VAULT_FILE = STATE_DIR / 'live_broker_credential_vault_state.json'
BROKER_SESSION_FILE = STATE_DIR / 'broker_session_handshake_state.json'
POST_TRADE_LOCK_FILE = STATE_DIR / 'live_position_reconciliation_post_trade_lock_state.json'
CASH_TRUTH_FILE = STATE_DIR / 'real_broker_cash_buying_power_margin_truth_state.json'


def _read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def _write_json(path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _load_execution() -> Dict[str, Any]:
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper', 'fills': [], 'orders': []})


def _load_risk() -> Dict[str, Any]:
    return _read_json(RISK_FILE, {
        'armed': True,
        'kill_switch_triggered': False,
        'kill_switch_level': 'normal',
        'trigger_reason': None,
        'summary': {'safe_mode': True, 'execution_mode': 'paper'},
        'metrics': {'daily_loss_pct': 0.0, 'portfolio_drawdown_pct': 0.0, 'open_notional': 0.0},
    })


def _load_strategy() -> Dict[str, Any]:
    return _read_json(STRATEGY_FILE, {'execution_mode': 'paper', 'safe_mode': True, 'deployment_profiles': [], 'current_plan': {'deployments': []}})


def _load_performance() -> Dict[str, Any]:
    return _read_json(PERFORMANCE_FILE, {'returns': []})


def _load_autonomous() -> Dict[str, Any]:
    return _read_json(AUTONOMOUS_FILE, {'policy': {'enabled': False}, 'decision_queue': []})


def _load_ledger() -> Dict[str, Any]:
    return _read_json(LEDGER_FILE, {'balance': 100000.0, 'available': 100000.0, 'allocated': 0.0, 'currency': 'USD', 'history': []})


def _load_broker_truth() -> Dict[str, Any]:
    return _read_json(BROKER_TRUTH_FILE, {'selected_broker': 'paper', 'preferred_live_broker': 'binance', 'live_path_armed': False})


def _load_broker_sync() -> Dict[str, Any]:
    return _read_json(SYNC_FILE, {'sync_status': 'idle', 'positions': [], 'fills': [], 'drift_detected': False})


def _load_pnl_truth() -> Dict[str, Any]:
    return _read_json(PNL_TRUTH_FILE, {})


def _load_credential_vault() -> Dict[str, Any]:
    return _read_json(CREDENTIAL_VAULT_FILE, {'execution_authorized': False, 'selected_broker': 'paper', 'providers': {}})


def _save_execution(data: Dict[str, Any]) -> Dict[str, Any]:
    return _write_json(EXECUTION_FILE, data)


def _save_risk(data: Dict[str, Any]) -> Dict[str, Any]:
    return _write_json(RISK_FILE, data)


def _save_strategy(data: Dict[str, Any]) -> Dict[str, Any]:
    return _write_json(STRATEGY_FILE, data)


def _save_autonomous(data: Dict[str, Any]) -> Dict[str, Any]:
    return _write_json(AUTONOMOUS_FILE, data)


def _live_readiness(execution: Dict[str, Any], risk: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
    safe_mode = bool(execution.get('safe_mode', True)) or bool(strategy.get('safe_mode', True)) or bool(risk.get('summary', {}).get('safe_mode', True))
    kill_switch = bool(risk.get('kill_switch_triggered', False))
    mode = str(execution.get('mode', 'paper'))
    broker = str(execution.get('active_broker', 'paper'))
    ready = mode == 'live' and not safe_mode and not kill_switch and broker != 'paper'
    blockers = []
    if mode != 'live':
        blockers.append('execution mode is not live')
    if safe_mode:
        blockers.append('safe mode is enabled')
    if kill_switch:
        blockers.append('risk kill switch is triggered')
    if broker == 'paper':
        blockers.append('active broker is paper')
    return {'ready': ready, 'blockers': blockers}


@router.get('/health')
def operator_health() -> Dict[str, Any]:
    execution = _load_execution()
    risk = _load_risk()
    strategy = _load_strategy()
    readiness = _live_readiness(execution, risk, strategy)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01A',
        'operator_mode': 'active',
        'live_ready': readiness['ready'],
        'blockers': readiness['blockers'],
    }


@router.get('/summary')
def operator_summary() -> Dict[str, Any]:
    execution = _load_execution()
    risk = _load_risk()
    strategy = _load_strategy()
    performance = _load_performance()
    autonomous = _load_autonomous()
    ledger = _load_ledger()
    broker_truth = _load_broker_truth()
    broker_sync = _load_broker_sync()
    pnl_truth = _load_pnl_truth()
    order_entry = _load_order_entry()
    credential_vault = _load_credential_vault()
    broker_session = _load_broker_session()
    post_trade_lock = _load_post_trade_lock()
    cash_truth = _load_cash_truth()

    profiles = strategy.get('deployment_profiles', [])
    deployments = strategy.get('current_plan', {}).get('deployments', [])
    active_profiles = [p for p in profiles if p.get('enabled', True) and str(p.get('status', '')).lower() in {'active', 'live', 'selected', 'standby'}]
    fills = execution.get('fills', [])
    latest_fill = fills[-1] if fills else None
    returns = performance.get('returns', [])
    latest_return = float((returns[-1] or {}).get('net_return', 0.0)) if returns else 0.0
    readiness = _live_readiness(execution, risk, strategy)

    return {
        'status': 'ok',
        'mission': 'QNT-REAL01A',
        'operator_mode': {
            'visible_panels': ['trade', 'performance', 'strategy', 'risk'],
            'advanced_console_path': 'institutional_console.html',
        },
        'capital': {
            'balance': round(float(ledger.get('balance', 0.0)), 2),
            'available': round(float(ledger.get('available', 0.0)), 2),
            'allocated': round(float(ledger.get('allocated', 0.0)), 2),
            'currency': ledger.get('currency', 'USD'),
        },
        'execution': {
            'mode': execution.get('mode', 'paper'),
            'safe_mode': bool(execution.get('safe_mode', True)),
            'active_broker': execution.get('active_broker', 'paper'),
            'orders_count': len(execution.get('orders', [])),
            'fills_count': len(fills),
            'latest_fill': latest_fill,
        },
        'performance': {
            'net_return': round(float(pnl_truth.get('net_return_pct', latest_return * 100.0)), 2),
            'daily_loss_pct': round(float(risk.get('metrics', {}).get('daily_loss_pct', 0.0)) * 100.0, 2),
            'drawdown_pct': round(float(risk.get('metrics', {}).get('portfolio_drawdown_pct', 0.0)) * 100.0, 2),
            'open_notional': round(float(pnl_truth.get('gross_exposure', risk.get('metrics', {}).get('open_notional', 0.0))), 2),
            'current_equity': round(float(pnl_truth.get('current_equity', ledger.get('balance', 0.0))), 2),
            'daily_pnl_value': round(float(pnl_truth.get('daily_pnl', 0.0)), 2),
            'unrealized_pnl': round(float(pnl_truth.get('unrealized_pnl', 0.0)), 2),
        },
        'strategy': {
            'current_regime': strategy.get('current_regime', 'unknown'),
            'liquidity_state': strategy.get('liquidity_state', 'unknown'),
            'active_profile_count': len(active_profiles),
            'deployment_count': len(deployments),
            'profiles': profiles[:6],
        },
        'risk': {
            'kill_switch_triggered': bool(risk.get('kill_switch_triggered', False)),
            'kill_switch_level': risk.get('kill_switch_level', 'normal'),
            'armed': bool(risk.get('armed', False)),
            'trigger_reason': risk.get('trigger_reason'),
            'safe_mode': bool(risk.get('summary', {}).get('safe_mode', True)),
        },
        'autonomy': {
            'enabled': bool(autonomous.get('policy', {}).get('enabled', False)),
            'queue_count': len(autonomous.get('decision_queue', [])),
        },
        'broker_truth': {
            'selected_broker': broker_truth.get('selected_broker', execution.get('active_broker', 'paper')),
            'preferred_live_broker': broker_truth.get('preferred_live_broker', 'binance'),
            'live_path_armed': bool(broker_truth.get('live_path_armed', False)),
        },
        'broker_sync': {
            'sync_status': broker_sync.get('sync_status', 'idle'),
            'position_count': len(broker_sync.get('positions', [])),
            'fill_count': len(broker_sync.get('fills', [])),
            'drift_detected': bool(broker_sync.get('drift_detected', False)),
        },
        'pnl_truth': {
            'truth_status': pnl_truth.get('truth_status', 'idle'),
            'current_equity': round(float(pnl_truth.get('current_equity', ledger.get('balance', 0.0))), 2),
            'gross_exposure': round(float(pnl_truth.get('gross_exposure', 0.0)), 2),
            'unrealized_pnl': round(float(pnl_truth.get('unrealized_pnl', 0.0)), 2),
        },
        'order_entry': {
            'surface_status': order_entry.get('surface_status', 'idle'),
            'submission_count': int(order_entry.get('submission_count', 0)),
            'blocked_count': int(order_entry.get('blocked_count', 0)),
            'last_submission': order_entry.get('last_submission'),
        },
        'credential_vault': {
            'selected_broker': credential_vault.get('selected_broker', broker_truth.get('selected_broker', execution.get('active_broker', 'paper'))),
            'execution_authorized': bool(credential_vault.get('execution_authorized', False)),
            'configured_provider_count': len([p for p in (credential_vault.get('providers') or {}).values() if isinstance(p, dict) and p.get('configured')]),
            'authorization_reason': credential_vault.get('authorization_reason'),
        },
        'broker_session': {
            'session_status': broker_session.get('session_status', 'idle'),
            'connectivity_status': broker_session.get('connectivity_status', 'unknown'),
            'handshake_valid': bool(broker_session.get('handshake_valid', False)),
            'connectivity_verified': bool(broker_session.get('connectivity_verified', False)),
            'selected_broker': broker_session.get('selected_broker', broker_truth.get('selected_broker', execution.get('active_broker', 'paper'))),
        },
        'credential_vault': {
            'selected_broker': credential_vault.get('selected_broker', broker_truth.get('selected_broker', execution.get('active_broker', 'paper'))),
            'execution_authorized': bool(credential_vault.get('execution_authorized', False)),
            'configured_provider_count': len([p for p in (credential_vault.get('providers') or {}).values() if isinstance(p, dict) and p.get('configured')]),
            'authorization_reason': credential_vault.get('authorization_reason'),
        },
        'post_trade_lock': {
            'reconciliation_status': post_trade_lock.get('reconciliation_status', 'idle'),
            'lock_status': post_trade_lock.get('lock_status', 'unlocked'),
            'drift_detected': bool(post_trade_lock.get('drift_detected', False)),
            'latest_fill_reference': post_trade_lock.get('latest_fill_reference'),
        },
        'cash_truth': {
            'truth_status': cash_truth.get('truth_status', 'idle'),
            'cash_balance': round(float(cash_truth.get('cash_balance', 0.0)), 2),
            'buying_power': round(float(cash_truth.get('buying_power', 0.0)), 2),
            'available_buying_power': round(float(cash_truth.get('available_buying_power', 0.0)), 2),
            'margin_excess': round(float(cash_truth.get('margin_excess', 0.0)), 2),
        },
        'live_readiness': readiness,
        'generated_at': int(time.time()),
    }


@router.post('/mode')
def operator_set_mode(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    requested_mode = str(payload.get('mode', '')).lower().strip()
    if requested_mode not in {'paper', 'live'}:
        raise HTTPException(status_code=400, detail='mode must be paper or live')

    execution = _load_execution()
    risk = _load_risk()
    strategy = _load_strategy()

    if requested_mode == 'live' and bool(execution.get('safe_mode', True)):
        raise HTTPException(status_code=400, detail='disable safe mode before switching to live mode')
    if requested_mode == 'live' and bool(risk.get('kill_switch_triggered', False)):
        raise HTTPException(status_code=400, detail='kill switch is triggered; reset risk posture before live mode')

    execution['mode'] = requested_mode
    strategy['execution_mode'] = requested_mode
    risk.setdefault('summary', {})['execution_mode'] = requested_mode
    _save_execution(execution)
    _save_strategy(strategy)
    _save_risk(risk)
    return {'status': 'ok', 'mode': requested_mode}


@router.post('/safe-mode')
def operator_set_safe_mode(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    enabled = bool(payload.get('enabled', True))
    execution = _load_execution()
    risk = _load_risk()
    strategy = _load_strategy()
    autonomous = _load_autonomous()

    execution['safe_mode'] = enabled
    strategy['safe_mode'] = enabled
    risk.setdefault('summary', {})['safe_mode'] = enabled
    if enabled:
        execution['mode'] = 'paper'
        strategy['execution_mode'] = 'paper'
        risk.setdefault('summary', {})['execution_mode'] = 'paper'
    autonomous.setdefault('policy', {})['auto_execute_live'] = not enabled

    _save_execution(execution)
    _save_strategy(strategy)
    _save_risk(risk)
    _save_autonomous(autonomous)
    return {'status': 'ok', 'safe_mode': enabled, 'execution_mode': execution.get('mode', 'paper')}


@router.post('/kill-switch')
def operator_kill_switch(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    action = str(payload.get('action', '')).lower().strip()
    if action not in {'trigger', 'reset'}:
        raise HTTPException(status_code=400, detail='action must be trigger or reset')

    risk = _load_risk()
    execution = _load_execution()
    strategy = _load_strategy()
    now = int(time.time())

    if action == 'trigger':
        reason = str(payload.get('reason') or 'manual operator trigger')
        risk['kill_switch_triggered'] = True
        risk['kill_switch_level'] = 'critical'
        risk['trigger_reason'] = reason
        risk['triggered_at'] = now
        risk.setdefault('summary', {})['safe_mode'] = True
        risk.setdefault('summary', {})['execution_mode'] = 'paper'
        execution['safe_mode'] = True
        execution['mode'] = 'paper'
        strategy['safe_mode'] = True
        strategy['execution_mode'] = 'paper'
    else:
        risk['kill_switch_triggered'] = False
        risk['kill_switch_level'] = 'normal'
        risk['trigger_reason'] = None
        risk['reset_at'] = now

    _save_risk(risk)
    _save_execution(execution)
    _save_strategy(strategy)
    return {'status': 'ok', 'kill_switch_triggered': risk['kill_switch_triggered'], 'kill_switch_level': risk['kill_switch_level']}
