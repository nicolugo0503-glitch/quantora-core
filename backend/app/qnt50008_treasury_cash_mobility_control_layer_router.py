from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.treasury_cash_mobility_models import (
    TreasuryApproveTransferRequest,
    TreasuryConfigurationRequest,
    TreasuryExecuteTransferRequest,
    TreasuryRebalanceRequest,
    TreasuryResetRequest,
    TreasuryStageTransferRequest,
    TreasurySyncRequest,
)
from backend.app.treasury_cash_mobility.engine import TreasuryCashMobilityEngine
from backend.app.treasury_cash_mobility.state_store import load_state

router = APIRouter(tags=['qnt50008-treasury-cash-mobility-control-layer'])
engine = TreasuryCashMobilityEngine()


@router.get('/treasury/health')
def qnt50008_treasury_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50008',
        'treasury_status': summary.get('treasury_status'),
        'cash_balance': summary.get('cash_balance'),
        'available_to_move': summary.get('available_to_move'),
        'break_count': summary.get('break_count'),
    }


@router.get('/treasury/state')
def qnt50008_treasury_state():
    return load_state()


@router.get('/treasury/summary')
def qnt50008_treasury_summary():
    return engine.summary()


@router.get('/treasury/transfers')
def qnt50008_treasury_transfers(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50008',
        'pending_transfers': state.get('pending_transfers', [])[:use_limit],
        'completed_transfers': state.get('completed_transfers', [])[:use_limit],
        'rejected_transfers': state.get('rejected_transfers', [])[:use_limit],
    }


@router.get('/treasury/liquidity')
def qnt50008_treasury_liquidity(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50008',
        'accounts': state.get('accounts', {}),
        'last_sync': state.get('last_sync'),
        'liquidity_snapshots': state.get('liquidity_snapshots', [])[:use_limit],
    }


@router.post('/treasury/configure')
def qnt50008_treasury_configure(payload: TreasuryConfigurationRequest = Body(default=TreasuryConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/treasury/sync-settlement')
def qnt50008_treasury_sync(payload: TreasurySyncRequest = Body(default=TreasurySyncRequest())):
    return engine.sync_settlement_context(payload.model_dump(exclude_none=True))


@router.post('/treasury/stage-transfer')
def qnt50008_treasury_stage_transfer(payload: TreasuryStageTransferRequest = Body(...)):
    try:
        return engine.stage_transfer(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/treasury/approve-transfer')
def qnt50008_treasury_approve_transfer(payload: TreasuryApproveTransferRequest = Body(...)):
    try:
        return engine.approve_transfer(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/treasury/execute-transfer')
def qnt50008_treasury_execute_transfer(payload: TreasuryExecuteTransferRequest = Body(...)):
    try:
        return engine.execute_transfer(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/treasury/rebalance')
def qnt50008_treasury_rebalance(payload: TreasuryRebalanceRequest = Body(default=TreasuryRebalanceRequest())):
    return engine.rebalance(payload.model_dump(exclude_none=True))


@router.post('/treasury/reset')
def qnt50008_treasury_reset(payload: TreasuryResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
