from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.autonomous_remediation_recovery.engine import AutonomousRemediationRecoveryEngine
from backend.app.autonomous_remediation_recovery.state_store import load_state
from backend.app.models.autonomous_remediation_recovery_models import (
    AutonomousRecoveryAuthorizationRequest,
    AutonomousRecoveryClosureRequest,
    AutonomousRecoveryConfigurationRequest,
    AutonomousRecoveryExecutionRequest,
    AutonomousRecoveryResetRequest,
    AutonomousRecoverySyncRequest,
    RemediationActionRegistrationRequest,
)

router = APIRouter(tags=['qnt50027-autonomous-remediation-controlled-recovery-orchestration'])
engine = AutonomousRemediationRecoveryEngine()


@router.get('/autonomous-remediation/health')
def qnt50027_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50027',
        'posture': summary.get('posture'),
        'action_count': summary.get('action_count'),
        'recovery_cycle_count': summary.get('recovery_cycle_count'),
    }


@router.get('/autonomous-remediation/state')
def qnt50027_state():
    return load_state()


@router.get('/autonomous-remediation/summary')
def qnt50027_summary():
    return engine.summary()


@router.get('/autonomous-remediation/actions')
def qnt50027_actions(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50027', 'remediation_actions': state.get('remediation_actions', [])[:use_limit]}


@router.get('/autonomous-remediation/recoveries')
def qnt50027_recoveries(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50027', 'recovery_cycles': state.get('recovery_cycles', [])[:use_limit]}


@router.post('/autonomous-remediation/configure')
def qnt50027_configure(payload: AutonomousRecoveryConfigurationRequest = Body(default=AutonomousRecoveryConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/autonomous-remediation/sync-context')
def qnt50027_sync(payload: AutonomousRecoverySyncRequest = Body(default=AutonomousRecoverySyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/autonomous-remediation/register-action')
def qnt50027_register_action(payload: RemediationActionRegistrationRequest = Body(...)):
    try:
        return engine.register_action(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/autonomous-remediation/authorize-recovery')
def qnt50027_authorize(payload: AutonomousRecoveryAuthorizationRequest = Body(...)):
    try:
        return engine.authorize_recovery(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/autonomous-remediation/execute-recovery')
def qnt50027_execute(payload: AutonomousRecoveryExecutionRequest = Body(...)):
    try:
        return engine.execute_recovery(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/autonomous-remediation/close-action')
def qnt50027_close(payload: AutonomousRecoveryClosureRequest = Body(...)):
    try:
        return engine.close_action(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/autonomous-remediation/reset')
def qnt50027_reset(payload: AutonomousRecoveryResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
