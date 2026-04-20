from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.execution.fill_handler import append_audit, load_state, save_state
from backend.app.execution.order_router import OrderRouter
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.models.execution_models import BrokerActivationRequest, ExecutionEnvelope, ExecutionModeUpdate

router = APIRouter(tags=['qnt50001-live-broker-integration-layer'])


@router.get('/execution/health')
def qnt50001_execution_health():
    state = load_state()
    risk_state = load_risk_state()
    return {
        'status': 'ok',
        'mission': 'QNT50001',
        'mode': state.get('mode', 'paper'),
        'safe_mode': bool(state.get('safe_mode', True)),
        'broker': state.get('active_broker', 'paper'),
        'live_execution_permitted': state.get('mode') == 'live' and not state.get('safe_mode', True),
        'risk_kill_switch_triggered': bool(risk_state.get('kill_switch_triggered', False)),
    }


@router.get('/execution/mode')
def qnt50001_execution_mode():
    state = load_state()
    return {
        'mission': 'QNT50001',
        'mode': state.get('mode', 'paper'),
        'safe_mode': bool(state.get('safe_mode', True)),
        'broker': state.get('active_broker', 'paper'),
    }


@router.get('/execution/logs')
def qnt50001_execution_logs(limit: int = 25):
    state = load_state()
    use_limit = max(1, min(int(limit), 100))
    return {
        'mission': 'QNT50001',
        'fills': state.get('fills', [])[:use_limit],
        'orders': state.get('orders', [])[:use_limit],
        'audit_log': state.get('audit_log', [])[:use_limit],
    }


@router.post('/execution/mode')
def qnt50001_set_execution_mode(payload: ExecutionModeUpdate = Body(...)):
    state = load_state()
    state['mode'] = payload.mode
    state['safe_mode'] = payload.safe_mode
    state['active_broker'] = payload.broker
    save_state(state)
    append_audit('execution_mode_updated', {
        'mode': payload.mode,
        'safe_mode': payload.safe_mode,
        'broker': payload.broker,
    })
    return qnt50001_execution_mode()


@router.post('/execution/activate-broker')
def qnt50001_activate_broker(payload: BrokerActivationRequest = Body(...)):
    state = load_state()
    if payload.broker == 'paper' and state.get('mode') == 'live':
        raise HTTPException(status_code=400, detail='paper broker cannot be active during live mode')
    state['active_broker'] = payload.broker
    save_state(state)
    append_audit('broker_activated', {'broker': payload.broker})
    return qnt50001_execution_mode()


@router.post('/execution/submit')
def qnt50001_submit_execution(payload: ExecutionEnvelope = Body(...)):
    envelope = payload.model_dump()
    try:
        response = OrderRouter().route(envelope)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        'mission': 'QNT50001',
        'status': 'accepted',
        'envelope': envelope,
        'execution': response,
    }
