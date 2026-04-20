from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.executive_capital_committee.engine import ExecutiveCapitalCommitteeEngine
from backend.app.executive_capital_committee.state_store import load_state
from backend.app.models.executive_capital_committee_models import (
    ExecutiveCapitalCommitteeApprovalRequest,
    ExecutiveCapitalCommitteeConfigurationRequest,
    ExecutiveCapitalCommitteeProposalRequest,
    ExecutiveCapitalCommitteeResetRequest,
    ExecutiveCapitalCommitteeSyncRequest,
    ExecutiveCapitalMemoryRecordRequest,
)

router = APIRouter(tags=['qnt50023-executive-ai-capital-committee-decision-memory'])
engine = ExecutiveCapitalCommitteeEngine()


@router.get('/executive-committee/health')
def qnt50023_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50023',
        'posture': summary.get('posture'),
        'memory_count': summary.get('memory_count'),
        'proposal_count': summary.get('proposal_count'),
        'decision_count': summary.get('decision_count'),
    }


@router.get('/executive-committee/state')
def qnt50023_state():
    return load_state()


@router.get('/executive-committee/summary')
def qnt50023_summary():
    return engine.summary()


@router.get('/executive-committee/memories')
def qnt50023_memories(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50023', 'decision_memories': state.get('decision_memories', [])[:use_limit]}


@router.get('/executive-committee/decisions')
def qnt50023_decisions(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50023',
        'committee_proposals': state.get('committee_proposals', [])[:use_limit],
        'committee_decisions': state.get('committee_decisions', [])[:use_limit],
    }


@router.post('/executive-committee/configure')
def qnt50023_configure(payload: ExecutiveCapitalCommitteeConfigurationRequest = Body(default=ExecutiveCapitalCommitteeConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/executive-committee/sync-context')
def qnt50023_sync(payload: ExecutiveCapitalCommitteeSyncRequest = Body(default=ExecutiveCapitalCommitteeSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/executive-committee/record-memory')
def qnt50023_record_memory(payload: ExecutiveCapitalMemoryRecordRequest = Body(...)):
    try:
        return engine.record_memory(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/executive-committee/propose')
def qnt50023_propose(payload: ExecutiveCapitalCommitteeProposalRequest = Body(...)):
    try:
        return engine.propose(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/executive-committee/approve')
def qnt50023_approve(payload: ExecutiveCapitalCommitteeApprovalRequest = Body(...)):
    try:
        return engine.approve(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/executive-committee/reset')
def qnt50023_reset(payload: ExecutiveCapitalCommitteeResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
