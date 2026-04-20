from __future__ import annotations

from fastapi import APIRouter, Body

from backend.app.models.risk_kill_switch_models import (
    KillSwitchOverrideRequest,
    RiskConfigurationRequest,
    RiskControlActionRequest,
    RiskMetricsUpdateRequest,
)
from backend.app.risk_control.engine import RiskKillSwitchEngine
from backend.app.risk_control.state_store import load_state

router = APIRouter(tags=['qnt50004-risk-kill-switch-system'])
engine = RiskKillSwitchEngine()


@router.get('/risk/health')
def qnt50004_risk_health():
    state = load_state()
    return {
        'status': 'ok',
        'mission': 'QNT50004',
        'armed': bool(state.get('armed', True)),
        'kill_switch_triggered': bool(state.get('kill_switch_triggered', False)),
        'kill_switch_level': state.get('kill_switch_level', 'normal'),
        'trigger_reason': state.get('trigger_reason'),
        'active_breach_count': len(state.get('active_breaches', [])),
    }


@router.get('/risk/state')
def qnt50004_risk_state():
    return load_state()


@router.get('/risk/summary')
def qnt50004_risk_summary():
    return engine.summary()


@router.post('/risk/configure')
def qnt50004_risk_configure(payload: RiskConfigurationRequest = Body(default=RiskConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/risk/metrics')
def qnt50004_risk_metrics(payload: RiskMetricsUpdateRequest = Body(default=RiskMetricsUpdateRequest())):
    return engine.update_metrics(payload.model_dump(exclude_none=True))


@router.post('/risk/evaluate')
def qnt50004_risk_evaluate(payload: RiskMetricsUpdateRequest = Body(default=RiskMetricsUpdateRequest())):
    return engine.evaluate({'metrics': payload.model_dump(exclude_none=True), 'source': 'manual_evaluation'})


@router.post('/risk/arm')
def qnt50004_risk_arm(payload: RiskControlActionRequest = Body(...)):
    return engine.arm(payload.model_dump(exclude_none=True))


@router.post('/risk/disarm')
def qnt50004_risk_disarm(payload: RiskControlActionRequest = Body(...)):
    return engine.disarm(payload.model_dump(exclude_none=True))


@router.post('/risk/reset')
def qnt50004_risk_reset(payload: RiskControlActionRequest = Body(...)):
    return engine.reset(payload.model_dump(exclude_none=True))


@router.post('/risk/override')
def qnt50004_risk_override(payload: KillSwitchOverrideRequest = Body(...)):
    return engine.override(payload.model_dump(exclude_none=True))


@router.get('/risk/triggers')
def qnt50004_risk_triggers(limit: int = 25):
    return engine.triggers(limit=limit)
