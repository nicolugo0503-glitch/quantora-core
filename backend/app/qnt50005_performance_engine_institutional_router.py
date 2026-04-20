from __future__ import annotations

from fastapi import APIRouter, Body

from backend.app.models.performance_engine_models import (
    NavSnapshotRequest,
    PerformanceConfigurationRequest,
    PerformanceRecomputeRequest,
)
from backend.app.performance_engine.engine import PerformanceEngine
from backend.app.performance_engine.state_store import load_state

router = APIRouter(tags=['qnt50005-performance-engine-institutional'])
engine = PerformanceEngine()


@router.get('/performance/health')
def qnt50005_performance_health():
    state = load_state()
    metrics = state.get('metrics') or {}
    investor_metrics = state.get('investor_metrics') or {}
    return {
        'status': 'ok',
        'mission': 'QNT50005',
        'snapshot_count': len(state.get('nav_series', [])),
        'latest_recompute_at': state.get('latest_recompute_at'),
        'latest_equity': investor_metrics.get('latest_equity'),
        'sharpe_ratio': metrics.get('sharpe_ratio'),
        'max_drawdown_pct': metrics.get('max_drawdown_pct'),
    }


@router.get('/performance/state')
def qnt50005_performance_state():
    return load_state()


@router.get('/performance/summary')
def qnt50005_performance_summary():
    return engine.summary()


@router.get('/performance/returns')
def qnt50005_performance_returns(limit: int = 250):
    return engine.returns_series(limit=limit)


@router.get('/performance/attribution')
def qnt50005_performance_attribution(limit: int = 25):
    return engine.attribution(limit=limit)


@router.get('/performance/investor-metrics')
def qnt50005_investor_metrics():
    state = load_state()
    return {
        'mission': 'QNT50005',
        'investor_metrics': state.get('investor_metrics', {}),
        'metrics': state.get('metrics', {}),
    }


@router.post('/performance/configure')
def qnt50005_performance_configure(payload: PerformanceConfigurationRequest = Body(default=PerformanceConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/performance/nav-snapshot')
def qnt50005_performance_nav_snapshot(payload: NavSnapshotRequest = Body(...)):
    return engine.register_nav_snapshot(payload.model_dump(exclude_none=True))


@router.post('/performance/recompute')
def qnt50005_performance_recompute(payload: PerformanceRecomputeRequest = Body(default=PerformanceRecomputeRequest())):
    return engine.recompute(payload.model_dump(exclude_none=True))
