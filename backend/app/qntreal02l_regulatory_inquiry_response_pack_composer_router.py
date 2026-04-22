import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Body

router = APIRouter(prefix='/regulatory-inquiry-response', tags=['regulatory-inquiry-response-pack-composer'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'

STATE_FILE = STATE_DIR / 'regulatory_inquiry_response_pack_state.json'
INTEGRITY_FILE = STATE_DIR / 'supervisory_audit_trail_integrity_verification_state.json'
ARCHIVE_FILE = STATE_DIR / 'supervisory_archive_retrieval_index_state.json'
CLOSURE_FILE = STATE_DIR / 'supervisory_incident_closure_permanent_record_seal_state.json'
PACKET_FILE = STATE_DIR / 'supervisory_incident_packet_evidence_bundle_state.json'
RETRIEVAL_FILE = STATE_DIR / 'supervisory_retrieval_packet_export_state.json'
EXCEPTION_QUEUE_FILE = STATE_DIR / 'event_state_consistency_exception_queue.json'
HOLD_FILE = STATE_DIR / 'exception_escalation_trading_hold_state.json'


def _read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _now() -> int:
    return int(time.time())


def _default_state() -> Dict[str, Any]:
    return {
        'mission': 'QNT-REAL02L',
        'inquiry_status': 'idle',
        'compose_status': 'idle',
        'certification_status': 'idle',
        'dispatch_status': 'idle',
        'hard_blocked': True,
        'blockers': ['no regulatory inquiry registered'],
        'open_inquiry_id': None,
        'open_inquiry_ref': None,
        'regulator': None,
        'inquiry_type': None,
        'inquiry_subject': None,
        'registered_at': None,
        'response_deadline': None,
        'last_compose_id': None,
        'last_composed_at': None,
        'last_certification_id': None,
        'last_certified_at': None,
        'last_certified_by': None,
        'last_dispatch_id': None,
        'last_dispatched_at': None,
        'compose_count': 0,
        'dispatch_count': 0,
        'history': [],
    }


def _append_history(state: Dict[str, Any], item: Dict[str, Any]) -> None:
    history = list(state.get('history') or [])
    history.append(item)
    state['history'] = history[-200:]


def _gather_evidence() -> Dict[str, Any]:
    integrity = _read_json(INTEGRITY_FILE, {})
    archive = _read_json(ARCHIVE_FILE, {'records': []})
    closure = _read_json(CLOSURE_FILE, {})
    packet = _read_json(PACKET_FILE, {})
    retrieval = _read_json(RETRIEVAL_FILE, {})
    exception_queue = _read_json(EXCEPTION_QUEUE_FILE, {'open_breaks': [], 'closed_breaks': []})
    hold = _read_json(HOLD_FILE, {})

    return {
        'integrity_ok': bool(integrity.get('integrity_ok', False)),
        'integrity_sealed': bool(integrity.get('integrity_sealed', False)),
        'seal_id': integrity.get('seal_id'),
        'seal_hash': integrity.get('seal_hash'),
        'chain_head': integrity.get('chain_head'),
        'chain_event_count': int(integrity.get('chain_event_count', 0)),
        'archive_records': list(archive.get('records') or []),
        'archive_retrieval_ready': bool(archive.get('retrieval_ready', False)),
        'last_record_ref': archive.get('last_record_ref') or closure.get('permanent_record_ref'),
        'last_packet_id': archive.get('last_packet_id') or packet.get('last_packet_id'),
        'incident_closed': bool(closure.get('closed', False)),
        'record_sealed': bool(closure.get('record_sealed', False)),
        'permanent_record_ref': closure.get('permanent_record_ref'),
        'packet_status': packet.get('packet_status', 'idle'),
        'last_export_id': retrieval.get('last_export_id') or retrieval.get('last_record_ref'),
        'open_breaks': list(exception_queue.get('open_breaks') or []),
        'closed_breaks': list(exception_queue.get('closed_breaks') or []),
        'hold_status': hold.get('hold_status', 'unknown'),
    }


def _evaluate_blockers(state: Dict[str, Any], evidence: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    if not state.get('open_inquiry_id'):
        blockers.append('no regulatory inquiry has been registered')
        return blockers
    if not evidence['integrity_ok']:
        blockers.append('audit trail integrity verification has not passed')
    if not evidence['integrity_sealed']:
        blockers.append('audit trail has not been sealed by supervisory attestation')
    if not evidence['incident_closed']:
        blockers.append('incident closure is not complete')
    if not evidence['record_sealed']:
        blockers.append('permanent incident record has not been sealed')
    if not evidence['archive_retrieval_ready']:
        blockers.append('archive retrieval index is not ready')
    if not evidence['archive_records']:
        blockers.append('no archived records are available for response composition')
    if evidence['open_breaks']:
        blockers.append(f"{len(evidence['open_breaks'])} open exception break(s) must be resolved before regulatory response")
    return blockers


def _compose_pack(state: Dict[str, Any], evidence: Dict[str, Any], actor: str) -> Dict[str, Any]:
    compose_id = f"regpk-{uuid.uuid4().hex[:12]}"
    now = _now()
    pack = {
        'compose_id': compose_id,
        'mission': 'QNT-REAL02L',
        'inquiry_id': state.get('open_inquiry_id'),
        'inquiry_ref': state.get('open_inquiry_ref'),
        'regulator': state.get('regulator'),
        'inquiry_type': state.get('inquiry_type'),
        'inquiry_subject': state.get('inquiry_subject'),
        'composed_at': now,
        'composed_by': actor,
        'response_deadline': state.get('response_deadline'),
        'audit_trail': {
            'integrity_ok': evidence['integrity_ok'],
            'integrity_sealed': evidence['integrity_sealed'],
            'seal_id': evidence['seal_id'],
            'seal_hash': evidence['seal_hash'],
            'chain_head': evidence['chain_head'],
            'chain_event_count': evidence['chain_event_count'],
        },
        'incident_record': {
            'incident_closed': evidence['incident_closed'],
            'record_sealed': evidence['record_sealed'],
            'permanent_record_ref': evidence['permanent_record_ref'],
        },
        'evidence_bundle': {
            'packet_status': evidence['packet_status'],
            'last_packet_id': evidence['last_packet_id'],
            'last_record_ref': evidence['last_record_ref'],
            'archive_record_count': len(evidence['archive_records']),
        },
        'exception_summary': {
            'open_breaks': len(evidence['open_breaks']),
            'closed_breaks': len(evidence['closed_breaks']),
            'hold_status': evidence['hold_status'],
        },
        'response_sections': [
            {'section': 'cover_letter', 'status': 'generated', 'content_ref': f"cover-{compose_id}"},
            {'section': 'audit_trail_attestation', 'status': 'generated', 'content_ref': evidence['seal_id'] or f"attest-{compose_id}"},
            {'section': 'incident_chronology', 'status': 'generated', 'content_ref': evidence['permanent_record_ref'] or f"chron-{compose_id}"},
            {'section': 'evidence_index', 'status': 'generated', 'content_ref': evidence['last_packet_id'] or f"evdx-{compose_id}"},
            {'section': 'exception_resolution_log', 'status': 'generated', 'content_ref': f"exclog-{compose_id}"},
            {'section': 'archive_retrieval_manifest', 'status': 'generated', 'content_ref': evidence['last_record_ref'] or f"mfst-{compose_id}"},
        ],
    }
    return pack


@router.get('/health')
def health() -> Dict[str, Any]:
    state = _read_json(STATE_FILE, _default_state())
    evidence = _gather_evidence()
    blockers = _evaluate_blockers(state, evidence)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02L',
        'inquiry_status': state.get('inquiry_status', 'idle'),
        'compose_status': state.get('compose_status', 'idle'),
        'certification_status': state.get('certification_status', 'idle'),
        'dispatch_status': state.get('dispatch_status', 'idle'),
        'hard_blocked': len(blockers) > 0,
    }


@router.get('/summary')
def summary() -> Dict[str, Any]:
    state = _read_json(STATE_FILE, _default_state())
    evidence = _gather_evidence()
    blockers = _evaluate_blockers(state, evidence)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02L',
        'inquiry_status': state.get('inquiry_status', 'idle'),
        'compose_status': state.get('compose_status', 'idle'),
        'certification_status': state.get('certification_status', 'idle'),
        'dispatch_status': state.get('dispatch_status', 'idle'),
        'hard_blocked': len(blockers) > 0,
        'blockers': blockers,
        'open_inquiry_id': state.get('open_inquiry_id'),
        'open_inquiry_ref': state.get('open_inquiry_ref'),
        'regulator': state.get('regulator'),
        'inquiry_type': state.get('inquiry_type'),
        'inquiry_subject': state.get('inquiry_subject'),
        'registered_at': state.get('registered_at'),
        'response_deadline': state.get('response_deadline'),
        'last_compose_id': state.get('last_compose_id'),
        'last_composed_at': state.get('last_composed_at'),
        'last_certification_id': state.get('last_certification_id'),
        'last_certified_at': state.get('last_certified_at'),
        'last_certified_by': state.get('last_certified_by'),
        'last_dispatch_id': state.get('last_dispatch_id'),
        'last_dispatched_at': state.get('last_dispatched_at'),
        'compose_count': int(state.get('compose_count', 0)),
        'dispatch_count': int(state.get('dispatch_count', 0)),
        'evidence_summary': {
            'integrity_ok': evidence['integrity_ok'],
            'integrity_sealed': evidence['integrity_sealed'],
            'incident_closed': evidence['incident_closed'],
            'archive_retrieval_ready': evidence['archive_retrieval_ready'],
            'open_breaks': len(evidence['open_breaks']),
        },
    }


@router.post('/register')
def register_inquiry(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    regulator = str(payload.get('regulator') or 'FINRA').strip()
    inquiry_type = str(payload.get('inquiry_type') or 'routine_exam').strip()
    inquiry_subject = str(payload.get('inquiry_subject') or 'trading operations').strip()
    inquiry_ref = str(payload.get('inquiry_ref') or '').strip() or f"inq-{uuid.uuid4().hex[:10]}"
    response_deadline = payload.get('response_deadline')

    state = _read_json(STATE_FILE, _default_state())
    now = _now()
    inquiry_id = f"reg-inq-{uuid.uuid4().hex[:10]}"
    state['mission'] = 'QNT-REAL02L'
    state['open_inquiry_id'] = inquiry_id
    state['open_inquiry_ref'] = inquiry_ref
    state['regulator'] = regulator
    state['inquiry_type'] = inquiry_type
    state['inquiry_subject'] = inquiry_subject
    state['registered_at'] = now
    state['response_deadline'] = response_deadline
    state['inquiry_status'] = 'registered'
    state['compose_status'] = 'idle'
    state['certification_status'] = 'idle'
    state['dispatch_status'] = 'idle'
    _append_history(state, {
        'action': 'register',
        'at': now,
        'inquiry_id': inquiry_id,
        'inquiry_ref': inquiry_ref,
        'regulator': regulator,
        'inquiry_type': inquiry_type,
    })
    _write_json(STATE_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02L',
        'registered': True,
        'inquiry_id': inquiry_id,
        'inquiry_ref': inquiry_ref,
        'regulator': regulator,
        'inquiry_type': inquiry_type,
    }


@router.post('/compose')
def compose_pack(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    actor = str(payload.get('actor') or 'compliance-officer').strip()
    state = _read_json(STATE_FILE, _default_state())
    evidence = _gather_evidence()
    blockers = _evaluate_blockers(state, evidence)
    now = _now()

    if blockers:
        return {
            'status': 'blocked',
            'mission': 'QNT-REAL02L',
            'composed': False,
            'blockers': blockers,
        }

    pack = _compose_pack(state, evidence, actor)
    compose_id = pack['compose_id']

    state['last_compose_id'] = compose_id
    state['last_composed_at'] = now
    state['compose_status'] = 'composed'
    state['compose_count'] = int(state.get('compose_count', 0)) + 1
    state['last_pack'] = pack
    _append_history(state, {'action': 'compose', 'at': now, 'by': actor, 'compose_id': compose_id})
    _write_json(STATE_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02L',
        'composed': True,
        'compose_id': compose_id,
        'inquiry_id': state.get('open_inquiry_id'),
        'regulator': state.get('regulator'),
        'section_count': len(pack['response_sections']),
        'response_sections': pack['response_sections'],
    }


@router.post('/certify')
def certify_pack(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    actor = str(payload.get('actor') or 'compliance-officer').strip()
    reason = str(payload.get('reason') or 'supervisory regulatory response certification').strip()
    state = _read_json(STATE_FILE, _default_state())
    now = _now()

    if not state.get('last_compose_id'):
        return {
            'status': 'blocked',
            'mission': 'QNT-REAL02L',
            'certified': False,
            'blockers': ['response pack has not been composed'],
        }

    evidence = _gather_evidence()
    blockers = _evaluate_blockers(state, evidence)
    if blockers:
        return {
            'status': 'blocked',
            'mission': 'QNT-REAL02L',
            'certified': False,
            'blockers': blockers,
        }

    certification_id = f"cert-{uuid.uuid4().hex[:12]}"
    state['last_certification_id'] = certification_id
    state['last_certified_at'] = now
    state['last_certified_by'] = actor
    state['certification_status'] = 'certified'
    _append_history(state, {
        'action': 'certify',
        'at': now,
        'by': actor,
        'certification_id': certification_id,
        'compose_id': state.get('last_compose_id'),
        'reason': reason,
    })
    _write_json(STATE_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02L',
        'certified': True,
        'certification_id': certification_id,
        'compose_id': state.get('last_compose_id'),
        'certified_by': actor,
        'reason': reason,
    }


@router.post('/dispatch')
def dispatch_pack(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    actor = str(payload.get('actor') or 'compliance-officer').strip()
    channel = str(payload.get('channel') or 'secure-portal').strip()
    state = _read_json(STATE_FILE, _default_state())
    now = _now()
    blockers: List[str] = []

    if not state.get('last_compose_id'):
        blockers.append('response pack has not been composed')
    if state.get('certification_status') != 'certified':
        blockers.append('response pack has not been certified')
    if blockers:
        return {
            'status': 'blocked',
            'mission': 'QNT-REAL02L',
            'dispatched': False,
            'blockers': blockers,
        }

    dispatch_id = f"disp-{uuid.uuid4().hex[:12]}"
    state['last_dispatch_id'] = dispatch_id
    state['last_dispatched_at'] = now
    state['dispatch_status'] = 'dispatched'
    state['dispatch_count'] = int(state.get('dispatch_count', 0)) + 1
    state['inquiry_status'] = 'responded'
    _append_history(state, {
        'action': 'dispatch',
        'at': now,
        'by': actor,
        'dispatch_id': dispatch_id,
        'channel': channel,
        'inquiry_id': state.get('open_inquiry_id'),
        'compose_id': state.get('last_compose_id'),
        'certification_id': state.get('last_certification_id'),
    })
    _write_json(STATE_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02L',
        'dispatched': True,
        'dispatch_id': dispatch_id,
        'channel': channel,
        'inquiry_id': state.get('open_inquiry_id'),
        'regulator': state.get('regulator'),
        'compose_id': state.get('last_compose_id'),
        'certification_id': state.get('last_certification_id'),
    }


@router.post('/reset')
def reset() -> Dict[str, Any]:
    _write_json(STATE_FILE, _default_state())
    return {'status': 'ok', 'mission': 'QNT-REAL02L', 'reset': True}
