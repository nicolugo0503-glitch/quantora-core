from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.live_strategy_scale_up.engine import LiveStrategyScaleUpEngine
from backend.app.live_strategy_scale_up.state_store import load_state
from backend.app.models.live_strategy_scale_up_models import (
    LiveStrategyScaleUpApprovalRequest,
    LiveStrategyScaleUpClosureRequest,
    LiveStrategyScaleUpConfigurationRequest,
    LiveStrategyScaleUpExecutionRequest,
    LiveStrategyScaleUpRegistrationRequest,
    LiveStrategyScaleUpResetRequest,
    LiveStrategyScaleUpSyncRequest,
)

router = APIRouter(tags=['qnt50030-live-strategy-scale-up-dynamic-capital-ramp-governance'])
engine = LiveStrategyScaleUpEngine()


@router.get('/strategy-scale-up/health')
def qnt50030_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50030',
        'posture': summary.get('posture'),
        'scale_case_count': summary.get('scale_case_count'),
        'ramp_event_count': summary.get('ramp_event_count'),
    }


@router.get('/strategy-scale-up/state')
def qnt50030_state():
    return load_state()


@router.get('/strategy-scale-up/summary')
def qnt50030_summary():
    return engine.summary()


@router.get('/strategy-scale-up/cases')
def qnt50030_cases(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50030', 'scale_cases': state.get('scale_cases', [])[:use_limit]}


@router.get('/strategy-scale-up/events')
def qnt50030_events(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50030', 'ramp_events': state.get('ramp_events', [])[:use_limit]}


@router.post('/strategy-scale-up/configure')
def qnt50030_configure(payload: LiveStrategyScaleUpConfigurationRequest = Body(default=LiveStrategyScaleUpConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/strategy-scale-up/sync-context')
def qnt50030_sync(payload: LiveStrategyScaleUpSyncRequest = Body(default=LiveStrategyScaleUpSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/strategy-scale-up/register-scale-case')
def qnt50030_register(payload: LiveStrategyScaleUpRegistrationRequest = Body(...)):
    try:
        return engine.register_scale_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-scale-up/approve-ramp')
def qnt50030_approve(payload: LiveStrategyScaleUpApprovalRequest = Body(...)):
    try:
        return engine.approve_ramp(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-scale-up/execute-ramp')
def qnt50030_execute(payload: LiveStrategyScaleUpExecutionRequest = Body(...)):
    try:
        return engine.execute_ramp(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-scale-up/close-scale-case')
def qnt50030_close(payload: LiveStrategyScaleUpClosureRequest = Body(...)):
    try:
        return engine.close_scale_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-scale-up/reset')
def qnt50030_reset(payload: LiveStrategyScaleUpResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
