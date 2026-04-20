from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.settlement_reconciliation_models import (
    ReconciliationRunRequest,
    SettlementConfirmRequest,
    SettlementControlConfigurationRequest,
    SettlementIngestRequest,
    SettlementResetRequest,
)
from backend.app.settlement_reconciliation.engine import SettlementReconciliationEngine
from backend.app.settlement_reconciliation.state_store import load_state

router = APIRouter(tags=['qnt50007-settlement-reconciliation-control-layer'])
engine = SettlementReconciliationEngine()


@router.get('/settlement/health')
def qnt50007_settlement_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50007',
        'pending_count': summary.get('pending_count', 0),
        'settled_count': summary.get('settled_count', 0),
        'break_count': summary.get('break_count', 0),
        'last_reconciliation_status': summary.get('last_reconciliation_status'),
    }


@router.get('/settlement/state')
def qnt50007_settlement_state():
    return load_state()


@router.get('/settlement/summary')
def qnt50007_settlement_summary():
    return engine.summary()


@router.get('/settlement/pending')
def qnt50007_settlement_pending(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50007',
        'pending_settlements': state.get('pending_settlements', [])[:use_limit],
        'settled_settlements': state.get('settled_settlements', [])[:use_limit],
    }


@router.get('/settlement/ledger')
def qnt50007_settlement_ledger(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50007',
        'cash_ledger': state.get('cash_ledger', [])[:use_limit],
        'position_ledger': state.get('position_ledger', [])[:use_limit],
        'positions': state.get('positions', {}),
        'cash_balance': state.get('cash_balance', 0.0),
    }


@router.get('/settlement/breaks')
def qnt50007_settlement_breaks(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50007',
        'last_reconciliation': state.get('last_reconciliation'),
        'reconciliation_breaks': state.get('reconciliation_breaks', [])[:use_limit],
    }


@router.post('/settlement/configure')
def qnt50007_settlement_configure(payload: SettlementControlConfigurationRequest = Body(default=SettlementControlConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/settlement/ingest-fills')
def qnt50007_settlement_ingest(payload: SettlementIngestRequest = Body(default=SettlementIngestRequest())):
    return engine.ingest_execution_fills(payload.model_dump(exclude_none=True))


@router.post('/settlement/confirm')
def qnt50007_settlement_confirm(payload: SettlementConfirmRequest = Body(...)):
    try:
        return engine.confirm_settlement(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/settlement/reconcile')
def qnt50007_settlement_reconcile(payload: ReconciliationRunRequest = Body(default=ReconciliationRunRequest())):
    return engine.reconcile(payload.model_dump(exclude_none=True))


@router.post('/settlement/reset')
def qnt50007_settlement_reset(payload: SettlementResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
