from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.models.regulatory_disclosure_delivery_models import (
    RegulatoryDisclosureConfigurationRequest,
    RegulatoryDisclosureReceiptRequest,
    RegulatoryDisclosureRegisterRequest,
    RegulatoryDisclosureResetRequest,
    RegulatoryDisclosureSyncRequest,
    SupervisoryAcknowledgementRequest,
)
from backend.app.regulatory_disclosure_delivery.engine import RegulatoryDisclosureDeliveryEngine
from backend.app.regulatory_disclosure_delivery.state_store import load_state

router = APIRouter(tags=['qnt50015-regulatory-disclosure-delivery-supervisory-acknowledgement-ledger'])
engine = RegulatoryDisclosureDeliveryEngine()


@router.get('/regulatory-disclosures/health')
def qnt50015_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50015',
        'posture': summary.get('posture'),
        'delivery_case_count': summary.get('delivery_case_count'),
        'delivery_receipt_count': summary.get('delivery_receipt_count'),
        'supervisory_acknowledgement_count': summary.get('supervisory_acknowledgement_count'),
    }


@router.get('/regulatory-disclosures/state')
def qnt50015_state():
    return load_state()


@router.get('/regulatory-disclosures/summary')
def qnt50015_summary():
    return engine.summary()


@router.get('/regulatory-disclosures/deliveries')
def qnt50015_deliveries(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50015',
        'delivery_cases': state.get('delivery_cases', [])[:use_limit],
        'delivery_receipts': state.get('delivery_receipts', [])[:use_limit],
    }


@router.get('/regulatory-disclosures/acknowledgements')
def qnt50015_acknowledgements(limit: int = 100):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {
        'mission': 'QNT50015',
        'supervisory_acknowledgements': state.get('supervisory_acknowledgements', [])[:use_limit],
        'exceptions': state.get('exceptions', [])[:use_limit],
    }


@router.post('/regulatory-disclosures/configure')
def qnt50015_configure(payload: RegulatoryDisclosureConfigurationRequest = Body(default=RegulatoryDisclosureConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/regulatory-disclosures/sync-context')
def qnt50015_sync_context(payload: RegulatoryDisclosureSyncRequest = Body(default=RegulatoryDisclosureSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/regulatory-disclosures/register-delivery')
def qnt50015_register_delivery(payload: RegulatoryDisclosureRegisterRequest = Body(...)):
    try:
        return engine.register_delivery(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/regulatory-disclosures/record-receipt')
def qnt50015_record_receipt(payload: RegulatoryDisclosureReceiptRequest = Body(...)):
    try:
        return engine.record_delivery_receipt(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/regulatory-disclosures/acknowledge')
def qnt50015_acknowledge(payload: SupervisoryAcknowledgementRequest = Body(...)):
    try:
        return engine.record_acknowledgement(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/regulatory-disclosures/reset')
def qnt50015_reset(payload: RegulatoryDisclosureResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
