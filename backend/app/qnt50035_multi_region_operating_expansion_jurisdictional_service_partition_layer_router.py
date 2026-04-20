from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.multi_region_service_partition_models import (
    MultiRegionServicePartitionApprovalRequest,
    MultiRegionServicePartitionClosureRequest,
    MultiRegionServicePartitionConfigurationRequest,
    MultiRegionServicePartitionExecutionRequest,
    MultiRegionServicePartitionRegistrationRequest,
    MultiRegionServicePartitionResetRequest,
    MultiRegionServicePartitionSyncRequest,
)
from backend.app.multi_region_service_partition.engine import MultiRegionServicePartitionEngine
from backend.app.multi_region_service_partition.state_store import load_state

router = APIRouter(tags=['qnt50035-multi-region-operating-expansion-jurisdictional-service-partition-layer'])
engine = MultiRegionServicePartitionEngine()


@router.get('/region-partition/health')
def qnt50035_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50035',
        'posture': summary.get('posture'),
        'expansion_case_count': summary.get('expansion_case_count'),
        'partition_event_count': summary.get('partition_event_count'),
    }


@router.get('/region-partition/state')
def qnt50035_state():
    return load_state()


@router.get('/region-partition/summary')
def qnt50035_summary():
    return engine.summary()


@router.get('/region-partition/cases')
def qnt50035_cases(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50035', 'expansion_cases': state.get('expansion_cases', [])[:use_limit]}


@router.get('/region-partition/events')
def qnt50035_events(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50035', 'partition_events': state.get('partition_events', [])[:use_limit]}


@router.post('/region-partition/configure')
def qnt50035_configure(payload: MultiRegionServicePartitionConfigurationRequest = Body(default=MultiRegionServicePartitionConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/region-partition/sync-context')
def qnt50035_sync(payload: MultiRegionServicePartitionSyncRequest = Body(default=MultiRegionServicePartitionSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/region-partition/register-case')
def qnt50035_register(payload: MultiRegionServicePartitionRegistrationRequest = Body(...)):
    try:
        return engine.register_expansion_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/region-partition/approve')
def qnt50035_approve(payload: MultiRegionServicePartitionApprovalRequest = Body(...)):
    try:
        return engine.approve_partition(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/region-partition/execute')
def qnt50035_execute(payload: MultiRegionServicePartitionExecutionRequest = Body(...)):
    try:
        return engine.execute_partition(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/region-partition/close-case')
def qnt50035_close(payload: MultiRegionServicePartitionClosureRequest = Body(...)):
    try:
        return engine.close_expansion_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/region-partition/reset')
def qnt50035_reset(payload: MultiRegionServicePartitionResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
