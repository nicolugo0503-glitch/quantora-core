from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.cross_border_service_routing.engine import CrossBorderServiceRoutingEngine
from backend.app.cross_border_service_routing.state_store import load_state
from backend.app.models.cross_border_service_routing_models import (
    CrossBorderServiceRoutingApprovalRequest,
    CrossBorderServiceRoutingClosureRequest,
    CrossBorderServiceRoutingConfigurationRequest,
    CrossBorderServiceRoutingExecutionRequest,
    CrossBorderServiceRoutingRegistrationRequest,
    CrossBorderServiceRoutingResetRequest,
    CrossBorderServiceRoutingSyncRequest,
)

router = APIRouter(tags=['qnt50036-cross-border-service-routing-regulatory-boundary-enforcement-layer'])
engine = CrossBorderServiceRoutingEngine()


@router.get('/cross-border-routing/health')
def qnt50036_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50036',
        'posture': summary.get('posture'),
        'route_case_count': summary.get('route_case_count'),
        'routing_event_count': summary.get('routing_event_count'),
    }


@router.get('/cross-border-routing/state')
def qnt50036_state():
    return load_state()


@router.get('/cross-border-routing/summary')
def qnt50036_summary():
    return engine.summary()


@router.get('/cross-border-routing/cases')
def qnt50036_cases(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50036', 'route_cases': state.get('route_cases', [])[:use_limit]}


@router.get('/cross-border-routing/events')
def qnt50036_events(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50036', 'routing_events': state.get('routing_events', [])[:use_limit]}


@router.post('/cross-border-routing/configure')
def qnt50036_configure(payload: CrossBorderServiceRoutingConfigurationRequest = Body(default=CrossBorderServiceRoutingConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/cross-border-routing/sync-context')
def qnt50036_sync(payload: CrossBorderServiceRoutingSyncRequest = Body(default=CrossBorderServiceRoutingSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/cross-border-routing/register-case')
def qnt50036_register(payload: CrossBorderServiceRoutingRegistrationRequest = Body(...)):
    try:
        return engine.register_route_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/cross-border-routing/approve')
def qnt50036_approve(payload: CrossBorderServiceRoutingApprovalRequest = Body(...)):
    try:
        return engine.approve_route(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/cross-border-routing/execute')
def qnt50036_execute(payload: CrossBorderServiceRoutingExecutionRequest = Body(...)):
    try:
        return engine.execute_route(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/cross-border-routing/close-case')
def qnt50036_close(payload: CrossBorderServiceRoutingClosureRequest = Body(...)):
    try:
        return engine.close_route_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/cross-border-routing/reset')
def qnt50036_reset(payload: CrossBorderServiceRoutingResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
