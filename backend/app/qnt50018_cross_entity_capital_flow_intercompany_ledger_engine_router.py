from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.intercompany_ledger.engine import IntercompanyLedgerEngine
from backend.app.intercompany_ledger.state_store import load_state
from backend.app.models.intercompany_ledger_models import (
    IntercompanyFlowApproveRequest,
    IntercompanyFlowPostRequest,
    IntercompanyFlowRegisterRequest,
    IntercompanyFlowSettleRequest,
    IntercompanyLedgerConfigurationRequest,
    IntercompanyLedgerResetRequest,
    IntercompanyLedgerSyncRequest,
)

router = APIRouter(tags=['qnt50018-cross-entity-capital-flow-intercompany-ledger-engine'])
engine = IntercompanyLedgerEngine()


@router.get('/intercompany-ledger/health')
def qnt50018_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50018',
        'posture': summary.get('posture'),
        'flow_case_count': summary.get('flow_case_count'),
        'journal_entry_count': summary.get('journal_entry_count'),
        'settlement_count': summary.get('settlement_count'),
    }


@router.get('/intercompany-ledger/state')
def qnt50018_state():
    return load_state()


@router.get('/intercompany-ledger/summary')
def qnt50018_summary():
    return engine.summary()


@router.get('/intercompany-ledger/flows')
def qnt50018_flows(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50018', 'flow_cases': state.get('flow_cases', [])[:use_limit], 'settlements': state.get('settlements', [])[:use_limit]}


@router.get('/intercompany-ledger/journal')
def qnt50018_journal(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50018', 'journal_entries': state.get('journal_entries', [])[:use_limit], 'exceptions': state.get('exceptions', [])[:use_limit]}


@router.post('/intercompany-ledger/configure')
def qnt50018_configure(payload: IntercompanyLedgerConfigurationRequest = Body(default=IntercompanyLedgerConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/intercompany-ledger/sync-context')
def qnt50018_sync(payload: IntercompanyLedgerSyncRequest = Body(default=IntercompanyLedgerSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/intercompany-ledger/register-flow')
def qnt50018_register(payload: IntercompanyFlowRegisterRequest = Body(...)):
    try:
        return engine.register_flow(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/intercompany-ledger/approve')
def qnt50018_approve(payload: IntercompanyFlowApproveRequest = Body(...)):
    try:
        return engine.approve_flow(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/intercompany-ledger/post')
def qnt50018_post(payload: IntercompanyFlowPostRequest = Body(...)):
    try:
        return engine.post_flow(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/intercompany-ledger/settle')
def qnt50018_settle(payload: IntercompanyFlowSettleRequest = Body(...)):
    try:
        return engine.settle_flow(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/intercompany-ledger/reset')
def qnt50018_reset(payload: IntercompanyLedgerResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
