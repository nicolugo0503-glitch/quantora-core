from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.investor_cash_confirmation.engine import InvestorCashConfirmationEngine
from backend.app.investor_cash_confirmation.state_store import load_state, transfer_release_status
from backend.app.models.investor_cash_confirmation_models import (
    InvestorCashAcknowledgementRequest,
    InvestorCashConfirmationConfigurationRequest,
    InvestorCashConfirmationResetRequest,
    InvestorCashConfirmationSyncRequest,
    InvestorRegistrationRequest,
    InvestorReleaseAuthorizeRequest,
    InvestorReleaseRequest,
)

router = APIRouter(tags=['qnt50009-investor-cash-confirmation-treasury-release-authority'])
engine = InvestorCashConfirmationEngine()


@router.get('/investor-cash-confirmation/health')
def qnt50009_investor_cash_confirmation_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50009',
        'posture': summary.get('posture'),
        'pending_release_count': summary.get('pending_release_count'),
        'authorized_release_count': summary.get('authorized_release_count'),
        'treasury_break_count': summary.get('treasury_break_count'),
    }


@router.get('/investor-cash-confirmation/state')
def qnt50009_investor_cash_confirmation_state():
    return load_state()


@router.get('/investor-cash-confirmation/summary')
def qnt50009_investor_cash_confirmation_summary():
    return engine.summary()


@router.get('/investor-cash-confirmation/releases')
def qnt50009_investor_cash_confirmation_releases(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50009',
        'pending_release_requests': state.get('pending_release_requests', [])[:use_limit],
        'authorized_releases': state.get('authorized_releases', [])[:use_limit],
        'rejected_releases': state.get('rejected_releases', [])[:use_limit],
    }


@router.get('/investor-cash-confirmation/transfer-status/{transfer_id}')
def qnt50009_investor_cash_confirmation_transfer_status(transfer_id: str):
    return {'mission': 'QNT50009', 'transfer_id': transfer_id, 'release_status': transfer_release_status(transfer_id)}


@router.post('/investor-cash-confirmation/configure')
def qnt50009_investor_cash_confirmation_configure(payload: InvestorCashConfirmationConfigurationRequest = Body(default=InvestorCashConfirmationConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/investor-cash-confirmation/sync-treasury')
def qnt50009_investor_cash_confirmation_sync(payload: InvestorCashConfirmationSyncRequest = Body(default=InvestorCashConfirmationSyncRequest())):
    return engine.sync_treasury_context(payload.model_dump(exclude_none=True))


@router.post('/investor-cash-confirmation/register-investor')
def qnt50009_investor_cash_confirmation_register_investor(payload: InvestorRegistrationRequest = Body(...)):
    try:
        return engine.register_investor(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-cash-confirmation/request-release')
def qnt50009_investor_cash_confirmation_request_release(payload: InvestorReleaseRequest = Body(...)):
    try:
        return engine.request_release(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-cash-confirmation/acknowledge')
def qnt50009_investor_cash_confirmation_acknowledge(payload: InvestorCashAcknowledgementRequest = Body(...)):
    try:
        return engine.acknowledge(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-cash-confirmation/authorize-release')
def qnt50009_investor_cash_confirmation_authorize_release(payload: InvestorReleaseAuthorizeRequest = Body(...)):
    try:
        return engine.authorize_release(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-cash-confirmation/reset')
def qnt50009_investor_cash_confirmation_reset(payload: InvestorCashConfirmationResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
