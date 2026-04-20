from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.executive_scenario_arbitration.engine import ExecutiveScenarioArbitrationEngine
from backend.app.executive_scenario_arbitration.state_store import load_state
from backend.app.models.executive_scenario_arbitration_models import (
    AllocationPolicyEnforcementRequest,
    AllocationPolicyRegistrationRequest,
    ExecutiveScenarioArbitrationConfigurationRequest,
    ExecutiveScenarioArbitrationRequest,
    ExecutiveScenarioArbitrationResetRequest,
    ExecutiveScenarioArbitrationSyncRequest,
)

router = APIRouter(tags=['qnt50024-executive-scenario-arbitration-allocation-policy-enforcement'])
engine = ExecutiveScenarioArbitrationEngine()


@router.get('/executive-arbitration/health')
def qnt50024_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50024',
        'posture': summary.get('posture'),
        'policy_count': summary.get('policy_count'),
        'scenario_count': summary.get('scenario_count'),
        'decision_count': summary.get('decision_count'),
    }


@router.get('/executive-arbitration/state')
def qnt50024_state():
    return load_state()


@router.get('/executive-arbitration/summary')
def qnt50024_summary():
    return engine.summary()


@router.get('/executive-arbitration/policies')
def qnt50024_policies(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50024', 'allocation_policies': state.get('allocation_policies', [])[:use_limit]}


@router.get('/executive-arbitration/scenarios')
def qnt50024_scenarios(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50024',
        'scenario_cases': state.get('scenario_cases', [])[:use_limit],
        'arbitration_decisions': state.get('arbitration_decisions', [])[:use_limit],
    }


@router.post('/executive-arbitration/configure')
def qnt50024_configure(payload: ExecutiveScenarioArbitrationConfigurationRequest = Body(default=ExecutiveScenarioArbitrationConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/executive-arbitration/sync-context')
def qnt50024_sync(payload: ExecutiveScenarioArbitrationSyncRequest = Body(default=ExecutiveScenarioArbitrationSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/executive-arbitration/register-policy')
def qnt50024_register_policy(payload: AllocationPolicyRegistrationRequest = Body(...)):
    try:
        return engine.register_policy(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/executive-arbitration/arbitrate')
def qnt50024_arbitrate(payload: ExecutiveScenarioArbitrationRequest = Body(...)):
    try:
        return engine.arbitrate(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/executive-arbitration/enforce-policy')
def qnt50024_enforce_policy(payload: AllocationPolicyEnforcementRequest = Body(...)):
    try:
        return engine.enforce_policy(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/executive-arbitration/reset')
def qnt50024_reset(payload: ExecutiveScenarioArbitrationResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
