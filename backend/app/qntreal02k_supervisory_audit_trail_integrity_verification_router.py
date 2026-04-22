import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Body

router = APIRouter(prefix='/supervisory-audit-integrity', tags=['supervisory-audit-trail-integrity-verification'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'

STATE_FILE = STATE_DIR / 'supervisory_audit_trail_integrity_verification_state.json'
EXPORT_DIR = STATE_DIR / 'supervisory_audit_trail_integrity_exports'
FILL_EVENTS_FILE = STATE_DIR / 'live_fill_event_stream_events.json'
ORDER_TIMELINE_FILE = STATE_DIR / 'broker_order_status_timeline.json'
EXCEPTION_QUEUE_FILE = STATE_DIR / 'event_state_consistency_exception_queue.json'
HOLD_FILE = STATE_DIR / 'exception_escalation_trading_hold_state.json'
RELEASE_FILE = STATE_DIR / 'supervisory_hold_release_certification_state.json'
CLOSURE_FILE = STATE_DIR / 'supervisory_incident_closure_permanent_record_seal_state.json'
ARCHIVE_FILE = STATE_DIR / 'supervisory_archive_retrieval_index_state.json'
PACKET_FILE = STATE_DIR / 'supervisory_incident_packet_evidence_bundle_state.json'
RETRIEVAL_FILE = STATE_DIR / 'supervisory_retrieval_packet_export_state.json'
LEDGER_FILE = STATE_DIR / 'execution_ledger_final_authority_state.json'

STAGE_ORDER = {
    'fill': 10,
    'order': 20,
    'incident': 30,
    'hold': 40,
    'release': 50,
    'closure': 60,
    'archive': 70,
}


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
        'mission': 'QNT-REAL02K',
        'verification_status': 'idle',
        'integrity_ok': False,
        'hard_blocked': True,
        'ledger_counts': {
            'fills': 0,
            'orders': 0,
            'incidents': 0,
            'holds': 0,
            'releases': 0,
            'closures': 0,
            'archives': 0,
            'ledger_events': 0,
        },
        'issues': [],
        'issue_counts': {'gaps': 0, 'orphans': 0, 'sequence_breaks': 0, 'hash_breaks': 0},
        'chain_head': None,
        'chain_event_count': 0,
        'last_run_at': None,
        'last_run_by': None,
        'last_attestation_id': None,
        'last_attested_at': None,
        'last_attested_by': None,
        'integrity_sealed': False,
        'seal_id': None,
        'seal_hash': None,
        'seal_reason': None,
        'export_ready': False,
        'last_export_id': None,
        'last_exported_at': None,
        'history': [],
        'latest_snapshot': {},
    }


def _append_history(state: Dict[str, Any], item: Dict[str, Any]) -> None:
    history = list(state.get('history') or [])
    history.append(item)
    state['history'] = history[-200:]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _event_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
    return _sha(prev_hash + '|' + _canonical(payload))


def _event_ref(row: Dict[str, Any], prefix: str) -> str:
    explicit = str(row.get('event_id') or row.get('record_ref') or row.get('packet_id') or '').strip()
    if explicit:
        return explicit
    base = row.get('order_id') or row.get('break_id') or row.get('retrieval_key') or row.get('permanent_record_ref') or uuid.uuid4().hex[:12]
    return f'{prefix}-{base}'


def _fill_events() -> List[Dict[str, Any]]:
    payload = _read_json(FILL_EVENTS_FILE, {'events': []})
    events = []
    for item in list(payload.get('events') or []):
        events.append({
            'stage': 'fill',
            'stage_rank': STAGE_ORDER['fill'],
            'event_ref': _event_ref(item, 'fill'),
            'timestamp': int(item.get('executed_at') or item.get('ingested_at') or _now()),
            'order_id': str(item.get('order_id') or '').strip(),
            'record_ref': None,
            'source': 'live_fill_event_stream_events.json',
            'payload': {
                'broker': item.get('broker'),
                'symbol': item.get('symbol'),
                'side': item.get('side'),
                'filled_qty': item.get('filled_qty'),
                'fill_price': item.get('fill_price'),
                'broker_fill_id': item.get('broker_fill_id'),
            },
        })
    ledger = _read_json(LEDGER_FILE, {})
    for item in list(ledger.get('history') or []):
        if item.get('lifecycle_stage') == 'filled':
            events.append({
                'stage': 'fill',
                'stage_rank': STAGE_ORDER['fill'],
                'event_ref': _event_ref(item, 'ledgerfill'),
                'timestamp': int(item.get('recorded_at') or item.get('acknowledged_at') or _now()),
                'order_id': str(item.get('order_id') or '').strip(),
                'record_ref': None,
                'source': 'execution_ledger_final_authority_state.json',
                'payload': {
                    'lifecycle_stage': item.get('lifecycle_stage'),
                    'filled_qty': item.get('filled_qty'),
                },
            })
    return sorted(events, key=lambda x: (x['timestamp'], x['event_ref']))


def _order_events() -> List[Dict[str, Any]]:
    payload = _read_json(ORDER_TIMELINE_FILE, {'timelines': {}})
    events = []
    timelines = payload.get('timelines') or {}
    for order_id, timeline in timelines.items():
        transitions = list(timeline.get('transitions') or [])
        if transitions:
            for idx, tr in enumerate(transitions):
                events.append({
                    'stage': 'order',
                    'stage_rank': STAGE_ORDER['order'],
                    'event_ref': _event_ref(tr, f'order-{idx}'),
                    'timestamp': int(tr.get('at') or tr.get('timestamp') or _now()),
                    'order_id': str(order_id or timeline.get('order_id') or '').strip(),
                    'record_ref': None,
                    'source': 'broker_order_status_timeline.json',
                    'payload': {'state': tr.get('state'), 'from': tr.get('from'), 'to': tr.get('to')},
                })
        else:
            events.append({
                'stage': 'order',
                'stage_rank': STAGE_ORDER['order'],
                'event_ref': _event_ref(timeline, 'order'),
                'timestamp': int(timeline.get('updated_at') or timeline.get('last_update_at') or _now()),
                'order_id': str(order_id or timeline.get('order_id') or '').strip(),
                'record_ref': None,
                'source': 'broker_order_status_timeline.json',
                'payload': {'state': timeline.get('current_state'), 'terminal': timeline.get('terminal')},
            })
    return sorted(events, key=lambda x: (x['timestamp'], x['event_ref']))


def _incident_events() -> List[Dict[str, Any]]:
    payload = _read_json(EXCEPTION_QUEUE_FILE, {'open_breaks': [], 'closed_breaks': []})
    events = []
    for bucket, status in [('open_breaks', 'open'), ('closed_breaks', 'closed')]:
        for item in list(payload.get(bucket) or []):
            events.append({
                'stage': 'incident',
                'stage_rank': STAGE_ORDER['incident'],
                'event_ref': _event_ref(item, 'incident'),
                'timestamp': int(item.get('created_at') or item.get('opened_at') or item.get('closed_at') or _now()),
                'order_id': str(item.get('order_id') or '').strip(),
                'record_ref': None,
                'source': 'event_state_consistency_exception_queue.json',
                'payload': {'break_id': item.get('break_id'), 'severity': item.get('severity'), 'status': status},
            })
    return sorted(events, key=lambda x: (x['timestamp'], x['event_ref']))


def _hold_events() -> List[Dict[str, Any]]:
    payload = _read_json(HOLD_FILE, {'history': []})
    history = list(payload.get('history') or [])
    events = []
    if history:
        for item in history:
            events.append({
                'stage': 'hold',
                'stage_rank': STAGE_ORDER['hold'],
                'event_ref': _event_ref(item, 'hold'),
                'timestamp': int(item.get('at') or _now()),
                'order_id': str(item.get('order_id') or '').strip(),
                'record_ref': None,
                'source': 'exception_escalation_trading_hold_state.json',
                'payload': {'action': item.get('action'), 'hold_status': item.get('hold_status')},
            })
    elif str(payload.get('hold_status') or '').lower() == 'hold':
        events.append({
            'stage': 'hold',
            'stage_rank': STAGE_ORDER['hold'],
            'event_ref': 'hold-current',
            'timestamp': _now(),
            'order_id': '',
            'record_ref': None,
            'source': 'exception_escalation_trading_hold_state.json',
            'payload': {'hold_status': payload.get('hold_status'), 'escalation_status': payload.get('escalation_status')},
        })
    return sorted(events, key=lambda x: (x['timestamp'], x['event_ref']))


def _release_events() -> List[Dict[str, Any]]:
    payload = _read_json(RELEASE_FILE, {'history': []})
    history = list(payload.get('history') or [])
    events = []
    if history:
        for item in history:
            events.append({
                'stage': 'release',
                'stage_rank': STAGE_ORDER['release'],
                'event_ref': _event_ref(item, 'release'),
                'timestamp': int(item.get('at') or _now()),
                'order_id': str(item.get('order_id') or '').strip(),
                'record_ref': None,
                'source': 'supervisory_hold_release_certification_state.json',
                'payload': {'action': item.get('action'), 'release_status': item.get('release_status'), 'release_certified': item.get('release_certified')},
            })
    elif payload.get('release_status') not in (None, 'idle'):
        events.append({
            'stage': 'release',
            'stage_rank': STAGE_ORDER['release'],
            'event_ref': 'release-current',
            'timestamp': _now(),
            'order_id': '',
            'record_ref': None,
            'source': 'supervisory_hold_release_certification_state.json',
            'payload': {'release_status': payload.get('release_status'), 'hold_release_allowed': payload.get('hold_release_allowed'), 'release_certified': payload.get('release_certified')},
        })
    return sorted(events, key=lambda x: (x['timestamp'], x['event_ref']))


def _closure_events() -> List[Dict[str, Any]]:
    payload = _read_json(CLOSURE_FILE, {'history': []})
    history = list(payload.get('history') or [])
    events = []
    if history:
        for item in history:
            events.append({
                'stage': 'closure',
                'stage_rank': STAGE_ORDER['closure'],
                'event_ref': _event_ref(item, 'closure'),
                'timestamp': int(item.get('at') or _now()),
                'order_id': str(item.get('order_id') or '').strip(),
                'record_ref': str(item.get('record_ref') or payload.get('permanent_record_ref') or '').strip() or None,
                'source': 'supervisory_incident_closure_permanent_record_seal_state.json',
                'payload': {'action': item.get('action'), 'record_sealed': item.get('record_sealed')},
            })
    elif payload.get('closed') or payload.get('record_sealed'):
        events.append({
            'stage': 'closure',
            'stage_rank': STAGE_ORDER['closure'],
            'event_ref': 'closure-current',
            'timestamp': _now(),
            'order_id': '',
            'record_ref': str(payload.get('permanent_record_ref') or '').strip() or None,
            'source': 'supervisory_incident_closure_permanent_record_seal_state.json',
            'payload': {'closed': payload.get('closed'), 'record_sealed': payload.get('record_sealed')},
        })
    return sorted(events, key=lambda x: (x['timestamp'], x['event_ref']))


def _archive_events() -> List[Dict[str, Any]]:
    payload = _read_json(ARCHIVE_FILE, {'records': []})
    events = []
    for item in list(payload.get('records') or []):
        events.append({
            'stage': 'archive',
            'stage_rank': STAGE_ORDER['archive'],
            'event_ref': _event_ref(item, 'archive'),
            'timestamp': int(item.get('indexed_at') or item.get('created_at') or _now()),
            'order_id': '',
            'record_ref': str(item.get('record_ref') or '').strip() or None,
            'source': 'supervisory_archive_retrieval_index_state.json',
            'payload': {'packet_id': item.get('packet_id'), 'retrieval_key': item.get('retrieval_key')},
        })
    return sorted(events, key=lambda x: (x['timestamp'], x['event_ref']))


def _collect_ledgers() -> Dict[str, List[Dict[str, Any]]]:
    return {
        'fills': _fill_events(),
        'orders': _order_events(),
        'incidents': _incident_events(),
        'holds': _hold_events(),
        'releases': _release_events(),
        'closures': _closure_events(),
        'archives': _archive_events(),
    }


def _build_chain(ledgers: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], str]:
    chain = []
    prev_hash = 'GENESIS'
    for key in ['fills', 'orders', 'incidents', 'holds', 'releases', 'closures', 'archives']:
        for event in ledgers[key]:
            material = {
                'stage': event['stage'],
                'event_ref': event['event_ref'],
                'timestamp': event['timestamp'],
                'order_id': event['order_id'],
                'record_ref': event['record_ref'],
                'source': event['source'],
                'payload': event['payload'],
            }
            current_hash = _event_hash(prev_hash, material)
            chain.append({**event, 'prev_hash': prev_hash, 'hash': current_hash})
            prev_hash = current_hash
    return chain, prev_hash


def _detect_issues(ledgers: Dict[str, List[Dict[str, Any]]], chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    fill_order_ids = {e['order_id'] for e in ledgers['fills'] if e.get('order_id')}
    order_order_ids = {e['order_id'] for e in ledgers['orders'] if e.get('order_id')}
    closure_record_refs = {e['record_ref'] for e in ledgers['closures'] if e.get('record_ref')}
    archive_record_refs = {e['record_ref'] for e in ledgers['archives'] if e.get('record_ref')}

    if fill_order_ids and not order_order_ids:
        issues.append({'type': 'gap', 'severity': 'high', 'message': 'fill ledger exists without any order lifecycle ledger'})
    for order_id in sorted(fill_order_ids - order_order_ids):
        issues.append({'type': 'orphan', 'severity': 'high', 'message': f'fill order_id {order_id} is missing from order lifecycle ledger', 'order_id': order_id})
    if ledgers['incidents'] and not ledgers['fills'] and not ledgers['orders']:
        issues.append({'type': 'orphan', 'severity': 'high', 'message': 'incident ledger exists without any fill or order evidence'})
    if ledgers['holds'] and not ledgers['incidents']:
        issues.append({'type': 'gap', 'severity': 'high', 'message': 'hold event exists without incident evidence'})
    if ledgers['releases'] and not ledgers['holds']:
        issues.append({'type': 'gap', 'severity': 'high', 'message': 'release certification exists without a hold record'})
    if ledgers['closures'] and not ledgers['releases']:
        issues.append({'type': 'gap', 'severity': 'high', 'message': 'closure exists without release certification evidence'})
    if ledgers['archives'] and not ledgers['closures']:
        issues.append({'type': 'gap', 'severity': 'high', 'message': 'archive record exists without closure evidence'})
    for record_ref in sorted(closure_record_refs - archive_record_refs):
        issues.append({'type': 'orphan', 'severity': 'high', 'message': f'closure record_ref {record_ref} is not present in archive index', 'record_ref': record_ref})

    last_rank = 0
    prev_hash = 'GENESIS'
    for idx, event in enumerate(chain):
        if event['stage_rank'] < last_rank:
            issues.append({'type': 'sequence_break', 'severity': 'critical', 'message': f"stage order regressed at {event['event_ref']}", 'event_ref': event['event_ref']})
        expected_hash = _event_hash(prev_hash, {
            'stage': event['stage'],
            'event_ref': event['event_ref'],
            'timestamp': event['timestamp'],
            'order_id': event['order_id'],
            'record_ref': event['record_ref'],
            'source': event['source'],
            'payload': event['payload'],
        })
        if event.get('prev_hash') != prev_hash or event.get('hash') != expected_hash:
            issues.append({'type': 'hash_break', 'severity': 'critical', 'message': f'hash chain mismatch at {event["event_ref"]}', 'event_ref': event['event_ref']})
        last_rank = max(last_rank, event['stage_rank'])
        prev_hash = event['hash']
        if idx and event['timestamp'] < chain[idx - 1]['timestamp']:
            issues.append({'type': 'sequence_break', 'severity': 'medium', 'message': f'timestamp moved backward at {event["event_ref"]}', 'event_ref': event['event_ref']})

    packet = _read_json(PACKET_FILE, {})
    retrieval = _read_json(RETRIEVAL_FILE, {})
    if packet.get('last_packet_id') and ledgers['archives']:
        packet_ids = {a['payload'].get('packet_id') for a in ledgers['archives']}
        if packet.get('last_packet_id') not in packet_ids:
            issues.append({'type': 'orphan', 'severity': 'high', 'message': 'latest incident packet id is missing from archive chain', 'packet_id': packet.get('last_packet_id')})
    if retrieval.get('last_record_ref') and closure_record_refs and retrieval.get('last_record_ref') not in closure_record_refs.union(archive_record_refs):
        issues.append({'type': 'orphan', 'severity': 'high', 'message': 'retrieval export references an unknown record_ref', 'record_ref': retrieval.get('last_record_ref')})
    return issues


def _counts(ledgers: Dict[str, List[Dict[str, Any]]], chain: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        'fills': len(ledgers['fills']),
        'orders': len(ledgers['orders']),
        'incidents': len(ledgers['incidents']),
        'holds': len(ledgers['holds']),
        'releases': len(ledgers['releases']),
        'closures': len(ledgers['closures']),
        'archives': len(ledgers['archives']),
        'ledger_events': len(chain),
    }


def _issue_counts(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {'gaps': 0, 'orphans': 0, 'sequence_breaks': 0, 'hash_breaks': 0}
    for item in issues:
        t = item.get('type')
        if t == 'gap':
            out['gaps'] += 1
        elif t == 'orphan':
            out['orphans'] += 1
        elif t == 'sequence_break':
            out['sequence_breaks'] += 1
        elif t == 'hash_break':
            out['hash_breaks'] += 1
    return out


def _snapshot(actor: str = 'system') -> Dict[str, Any]:
    state = _read_json(STATE_FILE, _default_state())
    ledgers = _collect_ledgers()
    chain, head = _build_chain(ledgers)
    issues = _detect_issues(ledgers, chain)
    counts = _counts(ledgers, chain)
    issue_counts = _issue_counts(issues)
    integrity_ok = len(issues) == 0 and counts['ledger_events'] > 0
    sealed = bool(state.get('integrity_sealed', False)) and integrity_ok and state.get('chain_head') == head
    snapshot = {
        'mission': 'QNT-REAL02K',
        'verification_status': 'verified' if integrity_ok else ('blocked' if counts['ledger_events'] else 'idle'),
        'integrity_ok': integrity_ok,
        'hard_blocked': not integrity_ok,
        'ledger_counts': counts,
        'issues': issues,
        'issue_counts': issue_counts,
        'chain_head': head if chain else None,
        'chain_event_count': len(chain),
        'last_run_at': _now(),
        'last_run_by': actor,
        'integrity_sealed': sealed,
        'seal_id': state.get('seal_id') if sealed else None,
        'seal_hash': state.get('seal_hash') if sealed else None,
        'seal_reason': state.get('seal_reason') if sealed else None,
        'export_ready': integrity_ok,
        'latest_snapshot': {
            'chain_tail': chain[-10:],
            'ledger_preview': {k: v[-5:] for k, v in ledgers.items()},
        },
    }
    return snapshot


def _persist_snapshot(actor: str = 'system') -> Dict[str, Any]:
    state = _read_json(STATE_FILE, _default_state())
    snap = _snapshot(actor)
    state.update(snap)
    state['mission'] = 'QNT-REAL02K'
    _append_history(state, {'action': 'verify', 'at': snap['last_run_at'], 'by': actor, 'integrity_ok': snap['integrity_ok'], 'issues': len(snap['issues'])})
    _write_json(STATE_FILE, state)
    return state


@router.get('/health')
def health() -> Dict[str, Any]:
    state = _persist_snapshot('health')
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02K',
        'verification_status': state.get('verification_status', 'idle'),
        'integrity_ok': bool(state.get('integrity_ok', False)),
        'integrity_sealed': bool(state.get('integrity_sealed', False)),
        'chain_event_count': int(state.get('chain_event_count', 0)),
    }


@router.get('/summary')
def summary() -> Dict[str, Any]:
    state = _persist_snapshot('summary')
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02K',
        'verification_status': state.get('verification_status', 'idle'),
        'integrity_ok': bool(state.get('integrity_ok', False)),
        'hard_blocked': bool(state.get('hard_blocked', True)),
        'integrity_sealed': bool(state.get('integrity_sealed', False)),
        'seal_id': state.get('seal_id'),
        'seal_hash': state.get('seal_hash'),
        'seal_reason': state.get('seal_reason'),
        'ledger_counts': state.get('ledger_counts', {}),
        'issue_counts': state.get('issue_counts', {}),
        'issues': state.get('issues', []),
        'chain_head': state.get('chain_head'),
        'chain_event_count': int(state.get('chain_event_count', 0)),
        'last_run_at': state.get('last_run_at'),
        'last_run_by': state.get('last_run_by'),
        'last_attestation_id': state.get('last_attestation_id'),
        'last_attested_at': state.get('last_attested_at'),
        'last_attested_by': state.get('last_attested_by'),
        'last_export_id': state.get('last_export_id'),
        'last_exported_at': state.get('last_exported_at'),
        'export_ready': bool(state.get('export_ready', False)),
        'latest_snapshot': state.get('latest_snapshot', {}),
    }


@router.post('/verify')
def verify(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    actor = str(payload.get('actor') or 'supervisor').strip()
    state = _persist_snapshot(actor)
    return {'status': 'ok', 'mission': 'QNT-REAL02K', **summary()}


@router.post('/attest')
def attest(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    actor = str(payload.get('actor') or 'supervisor').strip()
    reason = str(payload.get('reason') or 'supervisory integrity attestation').strip()
    state = _persist_snapshot(actor)
    if not state.get('integrity_ok'):
        return {
            'status': 'blocked',
            'mission': 'QNT-REAL02K',
            'attested': False,
            'issues': state.get('issues', []),
        }
    attestation_id = f'att-{uuid.uuid4().hex[:10]}'
    seal_hash = _sha(f"{state.get('chain_head')}|{actor}|{reason}|{state.get('last_run_at')}")
    state['last_attestation_id'] = attestation_id
    state['last_attested_at'] = _now()
    state['last_attested_by'] = actor
    state['integrity_sealed'] = True
    state['seal_id'] = f'seal-{uuid.uuid4().hex[:10]}'
    state['seal_hash'] = seal_hash
    state['seal_reason'] = reason
    _append_history(state, {'action': 'attest', 'at': state['last_attested_at'], 'by': actor, 'attestation_id': attestation_id, 'seal_id': state['seal_id']})
    _write_json(STATE_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02K',
        'attested': True,
        'attestation_id': attestation_id,
        'seal_id': state['seal_id'],
        'seal_hash': state['seal_hash'],
    }


@router.post('/export')
def export_evidence(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    actor = str(payload.get('actor') or 'supervisor').strip()
    target = str(payload.get('target') or 'audit').strip()
    state = _persist_snapshot(actor)
    if not state.get('integrity_ok'):
        return {
            'status': 'blocked',
            'mission': 'QNT-REAL02K',
            'exported': False,
            'issues': state.get('issues', []),
        }
    export_id = f'int-exp-{uuid.uuid4().hex[:10]}'
    export_payload = {
        'mission': 'QNT-REAL02K',
        'export_id': export_id,
        'target': target,
        'exported_at': _now(),
        'exported_by': actor,
        'verification_status': state.get('verification_status'),
        'integrity_ok': state.get('integrity_ok'),
        'integrity_sealed': state.get('integrity_sealed'),
        'seal_id': state.get('seal_id'),
        'seal_hash': state.get('seal_hash'),
        'chain_head': state.get('chain_head'),
        'chain_event_count': state.get('chain_event_count'),
        'ledger_counts': state.get('ledger_counts'),
        'issue_counts': state.get('issue_counts'),
        'issues': state.get('issues'),
        'latest_snapshot': state.get('latest_snapshot'),
    }
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_file = EXPORT_DIR / f'{export_id}.json'
    export_file.write_text(json.dumps(export_payload, indent=2), encoding='utf-8')
    state['last_export_id'] = export_id
    state['last_exported_at'] = export_payload['exported_at']
    _append_history(state, {'action': 'export', 'at': state['last_exported_at'], 'by': actor, 'target': target, 'export_id': export_id})
    _write_json(STATE_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL02K',
        'exported': True,
        'export_id': export_id,
        'target': target,
        'export_path': str(export_file.relative_to(ROOT)),
    }


@router.post('/reset')
def reset() -> Dict[str, Any]:
    _write_json(STATE_FILE, _default_state())
    return {'status': 'ok', 'mission': 'QNT-REAL02K', 'reset': True}
