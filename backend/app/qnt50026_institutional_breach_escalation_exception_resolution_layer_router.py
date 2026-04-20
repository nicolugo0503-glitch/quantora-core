from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.institutional_breach_exception_resolution.engine import InstitutionalBreachExceptionResolutionEngine
from backend.app.institutional_breach_exception_resolution.state_store import load_state
from backend.app.models.institutional_breach_exception_resolution_models import (
    InstitutionalBreachCaseRegistrationRequest,
    InstitutionalBreachEscalationRequest,
    InstitutionalBreachExceptionConfigurationRequest,
    InstitutionalBreachExceptionResetRequest,
    InstitutionalBreachExceptionSyncRequest,
    InstitutionalExceptionResolutionRequest,
)

router = APIRouter(tags=['qnt50026-institutional-breach-escalation-exception-resolution'])
engine = InstitutionalBreachExceptionResolutionEngine()


@router.get('/institutional-breach/health')
def qnt50026_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50026',
        'posture': summary.get('posture'),
        'case_count': summary.get('case_count'),
        'resolution_count': summary.get('resolution_count'),
        'escalation_count': summary.get('escalation_count'),
    }


@router.get('/institutional-breach/state')
def qnt50026_state():
    return load_state()


@router.get('/institutional-breach/summary')
def qnt50026_summary():
    return engine.summary()


@router.get('/institutional-breach/cases')
def qnt50026_cases(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50026', 'breach_cases': state.get('breach_cases', [])[:use_limit]}


@router.get('/institutional-breach/resolutions')
def qnt50026_resolutions(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50026', 'exception_resolutions': state.get('exception_resolutions', [])[:use_limit]}


@router.get('/institutional-breach/escalations')
def qnt50026_escalations(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50026', 'escalation_log': state.get('escalation_log', [])[:use_limit]}


@router.post('/institutional-breach/configure')
def qnt50026_configure(payload: InstitutionalBreachExceptionConfigurationRequest = Body(default=InstitutionalBreachExceptionConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/institutional-breach/sync-context')
def qnt50026_sync(payload: InstitutionalBreachExceptionSyncRequest = Body(default=InstitutionalBreachExceptionSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/institutional-breach/register-case')
def qnt50026_register_case(payload: InstitutionalBreachCaseRegistrationRequest = Body(...)):
    try:
        return engine.register_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-breach/escalate')
def qnt50026_escalate(payload: InstitutionalBreachEscalationRequest = Body(...)):
    try:
        return engine.escalate_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-breach/resolve')
def qnt50026_resolve(payload: InstitutionalExceptionResolutionRequest = Body(...)):
    try:
        return engine.resolve_exception(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-breach/reset')
def qnt50026_reset(payload: InstitutionalBreachExceptionResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
