from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.investor_exit_finalization.engine import InvestorExitFinalizationEngine
from backend.app.investor_exit_finalization.state_store import exit_finalization_status, load_state
from backend.app.models.investor_exit_finalization_models import (
    InvestorExitAttestationRequest,
    InvestorExitAuthorizeRequest,
    InvestorExitCaseRequest,
    InvestorExitFinalizationConfigurationRequest,
    InvestorExitFinalizationResetRequest,
    InvestorExitFinalizeRequest,
    InvestorExitSyncRequest,
)

router = APIRouter(tags=['qnt50010-investor-redemption-settlement-exit-finalization-authority'])
engine = InvestorExitFinalizationEngine()


@router.get('/investor-exit/health')
def qnt50010_investor_exit_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50010',
        'posture': summary.get('posture'),
        'registered_case_count': summary.get('registered_case_count'),
        'authorized_case_count': summary.get('authorized_case_count'),
        'finalized_exit_count': summary.get('finalized_exit_count'),
        'settlement_break_count': summary.get('settlement_break_count'),
    }


@router.get('/investor-exit/state')
def qnt50010_investor_exit_state():
    return load_state()


@router.get('/investor-exit/summary')
def qnt50010_investor_exit_summary():
    return engine.summary()


@router.get('/investor-exit/cases')
def qnt50010_investor_exit_cases(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50010',
        'registered_cases': state.get('registered_cases', [])[:use_limit],
        'blocked_cases': state.get('blocked_cases', [])[:use_limit],
    }


@router.get('/investor-exit/finalizations')
def qnt50010_investor_exit_finalizations(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50010',
        'authorized_exit_finalizations': state.get('authorized_exit_finalizations', [])[:use_limit],
        'finalized_exits': state.get('finalized_exits', [])[:use_limit],
    }


@router.get('/investor-exit/status/{case_id}')
def qnt50010_investor_exit_status(case_id: str):
    return {'mission': 'QNT50010', 'case_id': case_id, 'exit_finalization_status': exit_finalization_status(case_id)}


@router.post('/investor-exit/configure')
def qnt50010_investor_exit_configure(payload: InvestorExitFinalizationConfigurationRequest = Body(default=InvestorExitFinalizationConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/investor-exit/sync-context')
def qnt50010_investor_exit_sync(payload: InvestorExitSyncRequest = Body(default=InvestorExitSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/investor-exit/register-case')
def qnt50010_investor_exit_register_case(payload: InvestorExitCaseRequest = Body(...)):
    try:
        return engine.register_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-exit/attest')
def qnt50010_investor_exit_attest(payload: InvestorExitAttestationRequest = Body(...)):
    try:
        return engine.attest(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-exit/authorize-finalization')
def qnt50010_investor_exit_authorize(payload: InvestorExitAuthorizeRequest = Body(...)):
    try:
        return engine.authorize_finalization(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-exit/finalize')
def qnt50010_investor_exit_finalize(payload: InvestorExitFinalizeRequest = Body(...)):
    try:
        return engine.finalize(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/investor-exit/reset')
def qnt50010_investor_exit_reset(payload: InvestorExitFinalizationResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
