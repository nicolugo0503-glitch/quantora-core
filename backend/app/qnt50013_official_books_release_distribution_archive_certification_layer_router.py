from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.official_books_archive_certification_models import (
    ArchiveCertificationRequest,
    OfficialBooksConfigurationRequest,
    OfficialBooksRegisterRequest,
    OfficialBooksReleaseRequest,
    OfficialBooksResetRequest,
    OfficialBooksSyncRequest,
)
from backend.app.official_books_archive_certification.engine import OfficialBooksArchiveCertificationEngine
from backend.app.official_books_archive_certification.state_store import load_state

router = APIRouter(tags=['qnt50013-official-books-release-distribution-archive-certification-layer'])
engine = OfficialBooksArchiveCertificationEngine()


@router.get('/official-books/health')
def qnt50013_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50013',
        'posture': summary.get('posture'),
        'books_release_count': summary.get('books_release_count'),
        'archive_certification_count': summary.get('archive_certification_count'),
        'official_release_count': summary.get('official_release_count'),
    }


@router.get('/official-books/state')
def qnt50013_state():
    return load_state()


@router.get('/official-books/summary')
def qnt50013_summary():
    return engine.summary()


@router.get('/official-books/releases')
def qnt50013_releases(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50013',
        'books_releases': state.get('books_releases', [])[:use_limit],
        'archive_certifications': state.get('archive_certifications', [])[:use_limit],
        'official_releases': state.get('official_releases', [])[:use_limit],
    }


@router.post('/official-books/configure')
def qnt50013_configure(payload: OfficialBooksConfigurationRequest = Body(default=OfficialBooksConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/official-books/sync-context')
def qnt50013_sync_context(payload: OfficialBooksSyncRequest = Body(default=OfficialBooksSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/official-books/register-release')
def qnt50013_register_release(payload: OfficialBooksRegisterRequest = Body(...)):
    try:
        return engine.register_release(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/official-books/certify-archive')
def qnt50013_certify_archive(payload: ArchiveCertificationRequest = Body(...)):
    try:
        return engine.certify_archive(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/official-books/release')
def qnt50013_release(payload: OfficialBooksReleaseRequest = Body(...)):
    try:
        return engine.release_official_books(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/official-books/reset')
def qnt50013_reset(payload: OfficialBooksResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
