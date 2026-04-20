from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.live_capital_reactivation.engine import LiveCapitalReactivationEngine
from backend.app.live_capital_reactivation.state_store import load_state
from backend.app.models.live_capital_reactivation_models import (
    LiveCapitalReactivationApprovalRequest,
    LiveCapitalReactivationClosureRequest,
    LiveCapitalReactivationConfigurationRequest,
    LiveCapitalReactivationExecutionRequest,
    LiveCapitalReactivationRegistrationRequest,
    LiveCapitalReactivationResetRequest,
    LiveCapitalReactivationSyncRequest,
)

router = APIRouter(tags=['qnt50029-live-capital-reactivation-strategy-reentry-governance'])
engine = LiveCapitalReactivationEngine()


@router.get('/strategy-reentry/health')
def qnt50029_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50029',
        'posture': summary.get('posture'),
        'reactivation_case_count': summary.get('reactivation_case_count'),
        'reentry_event_count': summary.get('reentry_event_count'),
    }


@router.get('/strategy-reentry/state')
def qnt50029_state():
    return load_state()


@router.get('/strategy-reentry/summary')
def qnt50029_summary():
    return engine.summary()


@router.get('/strategy-reentry/reactivations')
def qnt50029_reactivations(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50029', 'reactivation_cases': state.get('reactivation_cases', [])[:use_limit]}


@router.get('/strategy-reentry/events')
def qnt50029_events(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50029', 'reentry_events': state.get('reentry_events', [])[:use_limit]}


@router.post('/strategy-reentry/configure')
def qnt50029_configure(payload: LiveCapitalReactivationConfigurationRequest = Body(default=LiveCapitalReactivationConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/strategy-reentry/sync-context')
def qnt50029_sync(payload: LiveCapitalReactivationSyncRequest = Body(default=LiveCapitalReactivationSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/strategy-reentry/register-reactivation')
def qnt50029_register(payload: LiveCapitalReactivationRegistrationRequest = Body(...)):
    try:
        return engine.register_reactivation(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-reentry/approve-reentry')
def qnt50029_approve(payload: LiveCapitalReactivationApprovalRequest = Body(...)):
    try:
        return engine.approve_reentry(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-reentry/execute-reentry')
def qnt50029_execute(payload: LiveCapitalReactivationExecutionRequest = Body(...)):
    try:
        return engine.execute_reentry(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-reentry/close-reactivation')
def qnt50029_close(payload: LiveCapitalReactivationClosureRequest = Body(...)):
    try:
        return engine.close_reactivation(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-reentry/reset')
def qnt50029_reset(payload: LiveCapitalReactivationResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
