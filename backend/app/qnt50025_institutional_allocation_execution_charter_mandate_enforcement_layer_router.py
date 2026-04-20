from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.institutional_allocation_execution_charter.engine import InstitutionalAllocationExecutionCharterEngine
from backend.app.institutional_allocation_execution_charter.state_store import load_state
from backend.app.models.institutional_allocation_execution_charter_models import (
    InstitutionalAllocationExecutionCharterConfigurationRequest,
    InstitutionalAllocationExecutionCharterResetRequest,
    InstitutionalAllocationExecutionCharterSyncRequest,
    InstitutionalExecutionCharterRegistrationRequest,
    InstitutionalMandateEnforcementRequest,
    InstitutionalMandateRegistrationRequest,
)

router = APIRouter(tags=['qnt50025-institutional-allocation-execution-charter-mandate-enforcement'])
engine = InstitutionalAllocationExecutionCharterEngine()


@router.get('/institutional-charter/health')
def qnt50025_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50025',
        'posture': summary.get('posture'),
        'charter_count': summary.get('charter_count'),
        'mandate_count': summary.get('mandate_count'),
        'directive_count': summary.get('directive_count'),
    }


@router.get('/institutional-charter/state')
def qnt50025_state():
    return load_state()


@router.get('/institutional-charter/summary')
def qnt50025_summary():
    return engine.summary()


@router.get('/institutional-charter/charters')
def qnt50025_charters(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50025', 'execution_charters': state.get('execution_charters', [])[:use_limit]}


@router.get('/institutional-charter/mandates')
def qnt50025_mandates(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50025', 'mandates': state.get('mandates', [])[:use_limit]}


@router.get('/institutional-charter/directives')
def qnt50025_directives(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50025', 'enforcement_directives': state.get('enforcement_directives', [])[:use_limit]}


@router.post('/institutional-charter/configure')
def qnt50025_configure(payload: InstitutionalAllocationExecutionCharterConfigurationRequest = Body(default=InstitutionalAllocationExecutionCharterConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/institutional-charter/sync-context')
def qnt50025_sync(payload: InstitutionalAllocationExecutionCharterSyncRequest = Body(default=InstitutionalAllocationExecutionCharterSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/institutional-charter/register-charter')
def qnt50025_register_charter(payload: InstitutionalExecutionCharterRegistrationRequest = Body(...)):
    try:
        return engine.register_charter(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-charter/register-mandate')
def qnt50025_register_mandate(payload: InstitutionalMandateRegistrationRequest = Body(...)):
    try:
        return engine.register_mandate(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-charter/enforce-mandate')
def qnt50025_enforce_mandate(payload: InstitutionalMandateEnforcementRequest = Body(...)):
    try:
        return engine.enforce_mandate(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-charter/reset')
def qnt50025_reset(payload: InstitutionalAllocationExecutionCharterResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
