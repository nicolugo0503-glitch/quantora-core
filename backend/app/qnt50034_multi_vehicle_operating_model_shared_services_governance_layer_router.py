from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.multi_vehicle_shared_services_models import (
    MultiVehicleSharedServicesApprovalRequest,
    MultiVehicleSharedServicesClosureRequest,
    MultiVehicleSharedServicesConfigurationRequest,
    MultiVehicleSharedServicesExecutionRequest,
    MultiVehicleSharedServicesRegistrationRequest,
    MultiVehicleSharedServicesResetRequest,
    MultiVehicleSharedServicesSyncRequest,
)
from backend.app.multi_vehicle_shared_services.engine import MultiVehicleSharedServicesEngine
from backend.app.multi_vehicle_shared_services.state_store import load_state

router = APIRouter(tags=['qnt50034-multi-vehicle-operating-model-shared-services-governance'])
engine = MultiVehicleSharedServicesEngine()


@router.get('/shared-services/health')
def qnt50034_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50034',
        'posture': summary.get('posture'),
        'service_model_count': summary.get('service_model_count'),
        'service_event_count': summary.get('service_event_count'),
    }


@router.get('/shared-services/state')
def qnt50034_state():
    return load_state()


@router.get('/shared-services/summary')
def qnt50034_summary():
    return engine.summary()


@router.get('/shared-services/models')
def qnt50034_models(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50034', 'service_models': state.get('service_models', [])[:use_limit]}


@router.get('/shared-services/events')
def qnt50034_events(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50034', 'service_events': state.get('service_events', [])[:use_limit]}


@router.post('/shared-services/configure')
def qnt50034_configure(payload: MultiVehicleSharedServicesConfigurationRequest = Body(default=MultiVehicleSharedServicesConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/shared-services/sync-context')
def qnt50034_sync(payload: MultiVehicleSharedServicesSyncRequest = Body(default=MultiVehicleSharedServicesSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/shared-services/register-model')
def qnt50034_register(payload: MultiVehicleSharedServicesRegistrationRequest = Body(...)):
    try:
        return engine.register_service_model(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/shared-services/approve')
def qnt50034_approve(payload: MultiVehicleSharedServicesApprovalRequest = Body(...)):
    try:
        return engine.approve_service_model(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/shared-services/execute')
def qnt50034_execute(payload: MultiVehicleSharedServicesExecutionRequest = Body(...)):
    try:
        return engine.execute_service_model(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/shared-services/close-model')
def qnt50034_close(payload: MultiVehicleSharedServicesClosureRequest = Body(...)):
    try:
        return engine.close_service_model(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/shared-services/reset')
def qnt50034_reset(payload: MultiVehicleSharedServicesResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
