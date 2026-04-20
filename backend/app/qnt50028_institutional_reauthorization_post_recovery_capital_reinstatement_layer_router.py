from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.post_recovery_capital_reinstatement_models import (
    PostRecoveryCapitalReauthorizationClosureRequest,
    PostRecoveryCapitalReauthorizationRegistrationRequest,
    PostRecoveryCapitalReinstatementApprovalRequest,
    PostRecoveryCapitalReinstatementConfigurationRequest,
    PostRecoveryCapitalReinstatementExecutionRequest,
    PostRecoveryCapitalReinstatementResetRequest,
    PostRecoveryCapitalReinstatementSyncRequest,
)
from backend.app.post_recovery_capital_reinstatement.engine import PostRecoveryCapitalReinstatementEngine
from backend.app.post_recovery_capital_reinstatement.state_store import load_state

router = APIRouter(tags=['qnt50028-institutional-reauthorization-post-recovery-capital-reinstatement'])
engine = PostRecoveryCapitalReinstatementEngine()


@router.get('/capital-reauthorization/health')
def qnt50028_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50028',
        'posture': summary.get('posture'),
        'reauthorization_count': summary.get('reauthorization_count'),
        'reinstatement_event_count': summary.get('reinstatement_event_count'),
    }


@router.get('/capital-reauthorization/state')
def qnt50028_state():
    return load_state()


@router.get('/capital-reauthorization/summary')
def qnt50028_summary():
    return engine.summary()


@router.get('/capital-reauthorization/reauthorizations')
def qnt50028_reauthorizations(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50028', 'reauthorizations': state.get('reauthorization_cases', [])[:use_limit]}


@router.get('/capital-reauthorization/reinstatements')
def qnt50028_reinstatements(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50028', 'reinstatement_events': state.get('reinstatement_events', [])[:use_limit]}


@router.post('/capital-reauthorization/configure')
def qnt50028_configure(payload: PostRecoveryCapitalReinstatementConfigurationRequest = Body(default=PostRecoveryCapitalReinstatementConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/capital-reauthorization/sync-context')
def qnt50028_sync(payload: PostRecoveryCapitalReinstatementSyncRequest = Body(default=PostRecoveryCapitalReinstatementSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/capital-reauthorization/register-reauthorization')
def qnt50028_register(payload: PostRecoveryCapitalReauthorizationRegistrationRequest = Body(...)):
    try:
        return engine.register_reauthorization(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/capital-reauthorization/approve-reinstatement')
def qnt50028_approve(payload: PostRecoveryCapitalReinstatementApprovalRequest = Body(...)):
    try:
        return engine.approve_reinstatement(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/capital-reauthorization/execute-reinstatement')
def qnt50028_execute(payload: PostRecoveryCapitalReinstatementExecutionRequest = Body(...)):
    try:
        return engine.execute_reinstatement(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/capital-reauthorization/close-reauthorization')
def qnt50028_close(payload: PostRecoveryCapitalReauthorizationClosureRequest = Body(...)):
    try:
        return engine.close_reauthorization(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/capital-reauthorization/reset')
def qnt50028_reset(payload: PostRecoveryCapitalReinstatementResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
