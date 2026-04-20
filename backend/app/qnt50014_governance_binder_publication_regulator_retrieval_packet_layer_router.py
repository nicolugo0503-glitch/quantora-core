from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.governance_binder_publication.engine import GovernanceBinderPublicationEngine
from backend.app.governance_binder_publication.state_store import load_state
from backend.app.models.governance_binder_publication_models import (
    GovernanceBinderConfigurationRequest,
    GovernanceBinderPublishRequest,
    GovernanceBinderRegisterRequest,
    GovernanceBinderResetRequest,
    GovernanceBinderSyncRequest,
    GovernanceRetrievalPacketRequest,
)

router = APIRouter(tags=['qnt50014-governance-binder-publication-regulator-retrieval-packet-layer'])
engine = GovernanceBinderPublicationEngine()


@router.get('/governance-binder/health')
def qnt50014_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50014',
        'posture': summary.get('posture'),
        'publication_case_count': summary.get('publication_case_count'),
        'retrieval_packet_count': summary.get('retrieval_packet_count'),
        'published_binder_count': summary.get('published_binder_count'),
    }


@router.get('/governance-binder/state')
def qnt50014_state():
    return load_state()


@router.get('/governance-binder/summary')
def qnt50014_summary():
    return engine.summary()


@router.get('/governance-binder/publications')
def qnt50014_publications(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50014',
        'publication_cases': state.get('publication_cases', [])[:use_limit],
        'published_binders': state.get('published_binders', [])[:use_limit],
    }


@router.get('/governance-binder/retrieval-packets')
def qnt50014_retrieval_packets(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50014',
        'retrieval_packets': state.get('retrieval_packets', [])[:use_limit],
        'exceptions': state.get('exceptions', [])[:use_limit],
    }


@router.post('/governance-binder/configure')
def qnt50014_configure(payload: GovernanceBinderConfigurationRequest = Body(default=GovernanceBinderConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/governance-binder/sync-context')
def qnt50014_sync_context(payload: GovernanceBinderSyncRequest = Body(default=GovernanceBinderSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/governance-binder/register-publication')
def qnt50014_register_publication(payload: GovernanceBinderRegisterRequest = Body(...)):
    try:
        return engine.register_publication(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/governance-binder/assemble-retrieval-packet')
def qnt50014_assemble_retrieval_packet(payload: GovernanceRetrievalPacketRequest = Body(...)):
    try:
        return engine.assemble_retrieval_packet(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/governance-binder/publish')
def qnt50014_publish(payload: GovernanceBinderPublishRequest = Body(...)):
    try:
        return engine.publish_binder(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/governance-binder/reset')
def qnt50014_reset(payload: GovernanceBinderResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
