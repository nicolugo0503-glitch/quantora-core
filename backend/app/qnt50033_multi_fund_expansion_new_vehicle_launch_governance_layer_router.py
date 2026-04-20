from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.multi_fund_expansion.engine import MultiFundExpansionEngine
from backend.app.multi_fund_expansion.state_store import load_state
from backend.app.models.multi_fund_expansion_models import (
    MultiFundExpansionApprovalRequest,
    MultiFundExpansionClosureRequest,
    MultiFundExpansionConfigurationRequest,
    MultiFundExpansionExecutionRequest,
    MultiFundExpansionRegistrationRequest,
    MultiFundExpansionResetRequest,
    MultiFundExpansionSyncRequest,
)

router = APIRouter(tags=['qnt50033-multi-fund-expansion-new-vehicle-launch-governance'])
engine = MultiFundExpansionEngine()


@router.get('/vehicle-launch/health')
def qnt50033_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50033',
        'posture': summary.get('posture'),
        'launch_case_count': summary.get('launch_case_count'),
        'launch_event_count': summary.get('launch_event_count'),
    }


@router.get('/vehicle-launch/state')
def qnt50033_state():
    return load_state()


@router.get('/vehicle-launch/summary')
def qnt50033_summary():
    return engine.summary()


@router.get('/vehicle-launch/cases')
def qnt50033_cases(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50033', 'launch_cases': state.get('launch_cases', [])[:use_limit]}


@router.get('/vehicle-launch/events')
def qnt50033_events(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50033', 'launch_events': state.get('launch_events', [])[:use_limit]}


@router.post('/vehicle-launch/configure')
def qnt50033_configure(payload: MultiFundExpansionConfigurationRequest = Body(default=MultiFundExpansionConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/vehicle-launch/sync-context')
def qnt50033_sync(payload: MultiFundExpansionSyncRequest = Body(default=MultiFundExpansionSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/vehicle-launch/register-case')
def qnt50033_register(payload: MultiFundExpansionRegistrationRequest = Body(...)):
    try:
        return engine.register_launch_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/vehicle-launch/approve')
def qnt50033_approve(payload: MultiFundExpansionApprovalRequest = Body(...)):
    try:
        return engine.approve_launch(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/vehicle-launch/execute')
def qnt50033_execute(payload: MultiFundExpansionExecutionRequest = Body(...)):
    try:
        return engine.execute_launch(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/vehicle-launch/close-case')
def qnt50033_close(payload: MultiFundExpansionClosureRequest = Body(...)):
    try:
        return engine.close_launch_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/vehicle-launch/reset')
def qnt50033_reset(payload: MultiFundExpansionResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
