
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.autonomous_control_loop.engine import AutonomousControlLoopEngine
from backend.app.autonomous_control_loop.state_store import load_state
from backend.app.models.autonomous_control_loop_models import (
    AutonomousControlLoopConfigurationRequest,
    AutonomousControlLoopExecuteRequest,
    AutonomousControlLoopPlanRequest,
    AutonomousControlLoopResetRequest,
    AutonomousControlLoopSyncRequest,
)

router = APIRouter(tags=['qnt50022-full-autonomous-hedge-fund-control-loop'])
engine = AutonomousControlLoopEngine()


@router.get('/autonomous-control/health')
def qnt50022_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50022',
        'posture': summary.get('posture'),
        'plan_count': summary.get('plan_count'),
        'cycle_count': summary.get('cycle_count'),
        'escalation_count': summary.get('escalation_count'),
    }


@router.get('/autonomous-control/state')
def qnt50022_state():
    return load_state()


@router.get('/autonomous-control/summary')
def qnt50022_summary():
    return engine.summary()


@router.get('/autonomous-control/plans')
def qnt50022_plans(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50022', 'control_plans': state.get('control_plans', [])[:use_limit]}


@router.get('/autonomous-control/cycles')
def qnt50022_cycles(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50022',
        'control_cycles': state.get('control_cycles', [])[:use_limit],
        'escalations': state.get('escalations', [])[:use_limit],
    }


@router.post('/autonomous-control/configure')
def qnt50022_configure(payload: AutonomousControlLoopConfigurationRequest = Body(default=AutonomousControlLoopConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/autonomous-control/sync-context')
def qnt50022_sync(payload: AutonomousControlLoopSyncRequest = Body(default=AutonomousControlLoopSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/autonomous-control/plan-loop')
def qnt50022_plan(payload: AutonomousControlLoopPlanRequest = Body(default=AutonomousControlLoopPlanRequest())):
    try:
        return engine.plan_loop(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/autonomous-control/execute-loop')
def qnt50022_execute(payload: AutonomousControlLoopExecuteRequest = Body(default=AutonomousControlLoopExecuteRequest())):
    try:
        return engine.execute_loop(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/autonomous-control/reset')
def qnt50022_reset(payload: AutonomousControlLoopResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
