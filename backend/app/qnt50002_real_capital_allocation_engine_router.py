from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.allocation.engine import AllocationEngine
from backend.app.allocation.state_store import load_state
from backend.app.models.allocation_models import (
    AllocationApprovalRequest,
    AllocationRecommendationRequest,
    RebalancePreviewRequest,
    StrategyProfile,
)

router = APIRouter(tags=['qnt50002-real-capital-allocation-engine'])
engine = AllocationEngine()


@router.get('/allocation/health')
def qnt50002_allocation_health():
    state = load_state()
    return {
        'status': 'ok',
        'mission': 'QNT50002',
        'capital': state.get('total_capital', 0.0),
        'safe_mode': bool(state.get('safe_mode', True)),
        'execution_mode': state.get('execution_mode', 'paper'),
        'latest_plan_status': (state.get('latest_plan') or {}).get('status', 'none'),
        'strategy_count': len(state.get('strategies', [])),
    }


@router.get('/allocation/state')
def qnt50002_allocation_state():
    return load_state()


@router.get('/allocation/summary')
def qnt50002_allocation_summary():
    return engine.summary()


@router.get('/allocation/strategies')
def qnt50002_allocation_strategies():
    return engine.list_strategies()


@router.post('/allocation/strategies/register')
def qnt50002_register_strategy(payload: StrategyProfile = Body(...)):
    return {
        'mission': 'QNT50002',
        'status': 'registered',
        'strategy': engine.register_strategy(payload.model_dump()),
    }


@router.post('/allocation/recommend')
def qnt50002_recommend(payload: AllocationRecommendationRequest = Body(...)):
    try:
        plan = engine.recommend(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        'mission': 'QNT50002',
        'status': 'proposed',
        'plan': plan,
    }


@router.post('/allocation/approve')
def qnt50002_approve(payload: AllocationApprovalRequest = Body(...)):
    try:
        plan = engine.approve(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        'mission': 'QNT50002',
        'status': 'approved',
        'plan': plan,
    }


@router.post('/allocation/rebalance-preview')
def qnt50002_rebalance_preview(payload: RebalancePreviewRequest = Body(...)):
    try:
        plan = engine.rebalance_preview(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        'mission': 'QNT50002',
        'status': 'previewed',
        'plan': plan,
    }


@router.get('/allocation/history')
def qnt50002_history(limit: int = 25):
    state = load_state()
    use_limit = max(1, min(int(limit), 100))
    return {
        'mission': 'QNT50002',
        'history': state.get('history', [])[:use_limit],
        'committee_log': state.get('committee_log', [])[:use_limit],
        'audit_log': state.get('audit_log', [])[:use_limit],
    }


@router.get('/allocation/execution-handoff')
def qnt50002_execution_handoff():
    return engine.execution_handoff()
