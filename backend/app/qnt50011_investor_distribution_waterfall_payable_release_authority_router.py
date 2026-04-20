from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.investor_distribution_payables.engine import InvestorDistributionPayablesEngine
from backend.app.investor_distribution_payables.state_store import distribution_release_status, load_state
from backend.app.models.investor_distribution_payables_models import (
    DistributionAttestationRequest,
    DistributionBatchAuthorizeRequest,
    DistributionBatchRequest,
    DistributionExecutionRecordRequest,
    DistributionPayableAuthorizeRequest,
    DistributionPayablesConfigurationRequest,
    DistributionPayablesSyncRequest,
    DistributionResetRequest,
    DistributionTransferBindRequest,
)

router = APIRouter(tags=['qnt50011-investor-distribution-waterfall-payable-release-authority'])
engine = InvestorDistributionPayablesEngine()


@router.get('/investor-distributions/health')
def qnt50011_distribution_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50011',
        'posture': summary.get('posture'),
        'distribution_batch_count': summary.get('distribution_batch_count'),
        'authorized_payable_release_count': summary.get('authorized_payable_release_count'),
        'executed_payable_count': summary.get('executed_payable_count'),
        'settlement_break_count': summary.get('settlement_break_count'),
    }


@router.get('/investor-distributions/state')
def qnt50011_distribution_state():
    return load_state()


@router.get('/investor-distributions/summary')
def qnt50011_distribution_summary():
    return engine.summary()


@router.get('/investor-distributions/batches')
def qnt50011_distribution_batches(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50011',
        'distribution_batches': state.get('distribution_batches', [])[:use_limit],
        'blocked_batches': state.get('blocked_batches', [])[:use_limit],
    }


@router.get('/investor-distributions/releases')
def qnt50011_distribution_releases(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50011',
        'transfer_links': state.get('transfer_links', [])[:use_limit],
        'authorized_payable_releases': state.get('authorized_payable_releases', [])[:use_limit],
        'executed_payables': state.get('executed_payables', [])[:use_limit],
    }


@router.get('/investor-distributions/transfer-status/{transfer_id}')
def qnt50011_distribution_transfer_status(transfer_id: str):
    return {'mission': 'QNT50011', 'transfer_id': transfer_id, 'distribution_release_status': distribution_release_status(transfer_id)}


@router.post('/investor-distributions/configure')
def qnt50011_distribution_configure(payload: DistributionPayablesConfigurationRequest = Body(default=DistributionPayablesConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/investor-distributions/sync-context')
def qnt50011_distribution_sync(payload: DistributionPayablesSyncRequest = Body(default=DistributionPayablesSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/investor-distributions/register-batch')
def qnt50011_distribution_register_batch(payload: DistributionBatchRequest = Body(...)):
    try:
        return engine.register_batch(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-distributions/attest')
def qnt50011_distribution_attest(payload: DistributionAttestationRequest = Body(...)):
    try:
        return engine.attest(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-distributions/authorize-batch')
def qnt50011_distribution_authorize_batch(payload: DistributionBatchAuthorizeRequest = Body(...)):
    try:
        return engine.authorize_batch(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-distributions/bind-transfer')
def qnt50011_distribution_bind_transfer(payload: DistributionTransferBindRequest = Body(...)):
    try:
        return engine.bind_transfer(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-distributions/authorize-payable')
def qnt50011_distribution_authorize_payable(payload: DistributionPayableAuthorizeRequest = Body(...)):
    try:
        return engine.authorize_payable(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-distributions/record-execution')
def qnt50011_distribution_record_execution(payload: DistributionExecutionRecordRequest = Body(...)):
    try:
        return engine.record_execution(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-distributions/reset')
def qnt50011_distribution_reset(payload: DistributionResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
