from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.autonomous_execution.engine import AutonomousExecutionEngine
from backend.app.autonomous_execution.state_store import load_state
from backend.app.models.autonomous_execution_models import AutonomousCycleRequest, AutonomousExecutionConfigurationRequest, AutonomousReleaseIngestRequest, AutonomousResetRequest

router = APIRouter(tags=['qnt50006-autonomous-execution-layer'])
engine = AutonomousExecutionEngine()


@router.get('/autonomous-execution/health')
def qnt50006_autonomous_execution_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50006',
        'gate_ready': bool((summary.get('gate') or {}).get('ready', False)),
        'queue_depth': (summary.get('queue_summary') or {}).get('queued_count', 0),
        'execution_mode': summary.get('execution_mode'),
        'safe_mode': summary.get('safe_mode'),
        'kill_switch_triggered': summary.get('kill_switch_triggered'),
        'last_cycle_status': (summary.get('last_cycle') or {}).get('status'),
    }


@router.get('/autonomous-execution/state')
def qnt50006_autonomous_execution_state():
    return load_state()


@router.get('/autonomous-execution/summary')
def qnt50006_autonomous_execution_summary():
    return engine.summary()


@router.get('/autonomous-execution/policy')
def qnt50006_autonomous_execution_policy():
    state = load_state()
    return {'mission': 'QNT50006', 'policy': state.get('policy', {}), 'price_map': state.get('price_map', {})}


@router.get('/autonomous-execution/queue')
def qnt50006_autonomous_execution_queue(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 200))
    return {'mission': 'QNT50006', 'decision_queue': state.get('decision_queue', [])[:use_limit], 'escalations': state.get('escalations', [])[:use_limit]}


@router.get('/autonomous-execution/cycles')
def qnt50006_autonomous_execution_cycles(limit: int = 25):
    state = load_state()
    use_limit = max(1, min(int(limit), 100))
    return {
        'mission': 'QNT50006',
        'last_plan': state.get('last_plan'),
        'last_cycle': state.get('last_cycle'),
        'cycle_history': state.get('cycle_history', [])[:use_limit],
        'audit_log': state.get('audit_log', [])[:use_limit],
    }


@router.post('/autonomous-execution/configure')
def qnt50006_autonomous_execution_configure(payload: AutonomousExecutionConfigurationRequest = Body(default=AutonomousExecutionConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/autonomous-execution/ingest-release')
def qnt50006_autonomous_execution_ingest_release(payload: AutonomousReleaseIngestRequest = Body(default=AutonomousReleaseIngestRequest())):
    try:
        return engine.ingest_release_queue(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/autonomous-execution/plan-cycle')
def qnt50006_autonomous_execution_plan_cycle(payload: AutonomousCycleRequest = Body(default=AutonomousCycleRequest())):
    return engine.plan_cycle(payload.model_dump(exclude_none=True))


@router.post('/autonomous-execution/execute-cycle')
def qnt50006_autonomous_execution_execute_cycle(payload: AutonomousCycleRequest = Body(default=AutonomousCycleRequest())):
    return engine.execute_cycle(payload.model_dump(exclude_none=True))


@router.post('/autonomous-execution/reset')
def qnt50006_autonomous_execution_reset(payload: AutonomousResetRequest = Body(...)):
    return engine.reset(payload.model_dump(exclude_none=True))
