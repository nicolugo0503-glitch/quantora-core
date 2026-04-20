from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.strategy_deployment_models import (
    DeploymentApprovalRequest,
    DeploymentEvaluationRequest,
    DeploymentProfile,
    DeploymentRegimeSwitchRequest,
)
from backend.app.strategy_deployment.engine import StrategyDeploymentEngine
from backend.app.strategy_deployment.state_store import load_state

router = APIRouter(tags=['qnt50003-strategy-deployment-engine'])
engine = StrategyDeploymentEngine()


@router.get('/strategy-deployment/health')
def qnt50003_strategy_deployment_health():
    state = load_state()
    current_plan = state.get('current_plan') or {}
    return {
        'status': 'ok',
        'mission': 'QNT50003',
        'safe_mode': bool(state.get('safe_mode', True)),
        'execution_mode': state.get('execution_mode', 'paper'),
        'current_regime': state.get('current_regime', 'neutral'),
        'profile_count': len(state.get('deployment_profiles', [])),
        'active_strategy_count': len(state.get('active_deployments', [])),
        'current_plan_status': current_plan.get('status', 'none'),
    }


@router.get('/strategy-deployment/state')
def qnt50003_strategy_deployment_state():
    return load_state()


@router.get('/strategy-deployment/summary')
def qnt50003_strategy_deployment_summary():
    return engine.summary()


@router.get('/strategy-deployment/profiles')
def qnt50003_strategy_deployment_profiles():
    return engine.list_profiles()


@router.post('/strategy-deployment/profiles/register')
def qnt50003_register_strategy_profile(payload: DeploymentProfile = Body(...)):
    return {
        'mission': 'QNT50003',
        'status': 'registered',
        'profile': engine.register_profile(payload.model_dump()),
    }


@router.post('/strategy-deployment/evaluate')
def qnt50003_evaluate_deployment(payload: DeploymentEvaluationRequest = Body(default=DeploymentEvaluationRequest())):
    try:
        plan = engine.evaluate(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        'mission': 'QNT50003',
        'status': 'proposed',
        'plan': plan,
    }


@router.post('/strategy-deployment/deploy')
def qnt50003_deploy(payload: DeploymentApprovalRequest = Body(...)):
    try:
        return engine.deploy(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/strategy-deployment/switch-regime')
def qnt50003_switch_regime(payload: DeploymentRegimeSwitchRequest = Body(...)):
    try:
        return engine.switch_regime(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/strategy-deployment/release-queue')
def qnt50003_release_queue():
    return engine.release_queue()


@router.get('/strategy-deployment/history')
def qnt50003_history(limit: int = 25):
    state = load_state()
    use_limit = max(1, min(int(limit), 100))
    return {
        'mission': 'QNT50003',
        'history': state.get('history', [])[:use_limit],
        'release_queue': state.get('release_queue', [])[:use_limit],
        'audit_log': state.get('audit_log', [])[:use_limit],
    }
