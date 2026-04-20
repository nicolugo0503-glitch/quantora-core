from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.period_close_distribution_ledger_models import (
    PeriodCloseDistributionConfigurationRequest,
    PeriodCloseDistributionSyncRequest,
    PeriodCloseFinalizeRequest,
    PeriodCloseLedgerFinalizeRequest,
    PeriodCloseNoticeFinalizeRequest,
    PeriodCloseRegisterRequest,
    PeriodCloseResetRequest,
)
from backend.app.period_close_distribution_ledger.engine import PeriodCloseDistributionLedgerEngine
from backend.app.period_close_distribution_ledger.state_store import load_state

router = APIRouter(tags=['qnt50012-period-close-distribution-ledger-investor-notice-finalization'])
engine = PeriodCloseDistributionLedgerEngine()


@router.get('/period-close-distributions/health')
def qnt50012_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50012',
        'posture': summary.get('posture'),
        'period_close_count': summary.get('period_close_count'),
        'closed_period_count': summary.get('closed_period_count'),
        'notice_finalization_count': summary.get('notice_finalization_count'),
    }


@router.get('/period-close-distributions/state')
def qnt50012_state():
    return load_state()


@router.get('/period-close-distributions/summary')
def qnt50012_summary():
    return engine.summary()


@router.get('/period-close-distributions/ledger')
def qnt50012_ledger(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50012',
        'period_closes': state.get('period_closes', [])[:use_limit],
        'ledger_finalizations': state.get('ledger_finalizations', [])[:use_limit],
        'closed_periods': state.get('closed_periods', [])[:use_limit],
    }


@router.get('/period-close-distributions/notices')
def qnt50012_notices(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 500))
    return {
        'mission': 'QNT50012',
        'notice_finalizations': state.get('notice_finalizations', [])[:use_limit],
        'exceptions': state.get('exceptions', [])[:use_limit],
    }


@router.post('/period-close-distributions/configure')
def qnt50012_configure(payload: PeriodCloseDistributionConfigurationRequest = Body(default=PeriodCloseDistributionConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/period-close-distributions/sync-context')
def qnt50012_sync_context(payload: PeriodCloseDistributionSyncRequest = Body(default=PeriodCloseDistributionSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/period-close-distributions/register-close')
def qnt50012_register_close(payload: PeriodCloseRegisterRequest = Body(...)):
    try:
        return engine.register_close(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/period-close-distributions/finalize-ledger')
def qnt50012_finalize_ledger(payload: PeriodCloseLedgerFinalizeRequest = Body(...)):
    try:
        return engine.finalize_ledger(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/period-close-distributions/finalize-notice')
def qnt50012_finalize_notice(payload: PeriodCloseNoticeFinalizeRequest = Body(...)):
    try:
        return engine.finalize_notice(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/period-close-distributions/close-period')
def qnt50012_close_period(payload: PeriodCloseFinalizeRequest = Body(...)):
    try:
        return engine.close_period(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/period-close-distributions/reset')
def qnt50012_reset(payload: PeriodCloseResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
