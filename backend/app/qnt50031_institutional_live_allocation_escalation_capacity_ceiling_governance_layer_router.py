from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.live_allocation_escalation.engine import LiveAllocationEscalationEngine
from backend.app.live_allocation_escalation.state_store import load_state
from backend.app.models.live_allocation_escalation_models import (
    LiveAllocationEscalationApprovalRequest,
    LiveAllocationEscalationClosureRequest,
    LiveAllocationEscalationConfigurationRequest,
    LiveAllocationEscalationExecutionRequest,
    LiveAllocationEscalationRegistrationRequest,
    LiveAllocationEscalationResetRequest,
    LiveAllocationEscalationSyncRequest,
)

router = APIRouter(tags=['qnt50031-institutional-live-allocation-escalation-capacity-ceiling-governance'])
engine = LiveAllocationEscalationEngine()


@router.get('/allocation-escalation/health')
def qnt50031_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50031',
        'posture': summary.get('posture'),
        'escalation_case_count': summary.get('escalation_case_count'),
        'escalation_event_count': summary.get('escalation_event_count'),
    }


@router.get('/allocation-escalation/state')
def qnt50031_state():
    return load_state()


@router.get('/allocation-escalation/summary')
def qnt50031_summary():
    return engine.summary()


@router.get('/allocation-escalation/cases')
def qnt50031_cases(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50031', 'escalation_cases': state.get('escalation_cases', [])[:use_limit]}


@router.get('/allocation-escalation/events')
def qnt50031_events(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50031', 'escalation_events': state.get('escalation_events', [])[:use_limit]}


@router.post('/allocation-escalation/configure')
def qnt50031_configure(payload: LiveAllocationEscalationConfigurationRequest = Body(default=LiveAllocationEscalationConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/allocation-escalation/sync-context')
def qnt50031_sync(payload: LiveAllocationEscalationSyncRequest = Body(default=LiveAllocationEscalationSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/allocation-escalation/register-case')
def qnt50031_register(payload: LiveAllocationEscalationRegistrationRequest = Body(...)):
    try:
        return engine.register_escalation_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/allocation-escalation/approve')
def qnt50031_approve(payload: LiveAllocationEscalationApprovalRequest = Body(...)):
    try:
        return engine.approve_escalation(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/allocation-escalation/execute')
def qnt50031_execute(payload: LiveAllocationEscalationExecutionRequest = Body(...)):
    try:
        return engine.execute_escalation(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/allocation-escalation/close-case')
def qnt50031_close(payload: LiveAllocationEscalationClosureRequest = Body(...)):
    try:
        return engine.close_escalation_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/allocation-escalation/reset')
def qnt50031_reset(payload: LiveAllocationEscalationResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
