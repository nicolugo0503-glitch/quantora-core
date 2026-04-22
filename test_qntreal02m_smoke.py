import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from modules.qnt_real02m.integrity import verify_integrity


client = TestClient(app)
ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / 'backend' / 'app' / 'state'


def _write(name, data):
    (STATE_DIR / name).write_text(json.dumps(data), encoding='utf-8')


def _seed_happy_path():
    _write('supervisory_audit_trail_integrity_verification_state.json', {
        'mission': 'QNT-REAL02K',
        'integrity_ok': True,
        'integrity_sealed': True,
        'seal_id': 'seal-abc123',
        'seal_hash': 'aabbcc',
        'chain_head': 'deadbeef',
        'chain_event_count': 8,
        'verification_status': 'verified',
    })
    _write('supervisory_archive_retrieval_index_state.json', {
        'retrieval_ready': True,
        'records': [{'record_ref': 'seal-001', 'packet_id': 'pkt-001', 'retrieval_key': 'archive-seal-001', 'indexed_at': 160}],
        'last_record_ref': 'seal-001',
        'last_packet_id': 'pkt-001',
    })
    _write('supervisory_incident_closure_permanent_record_seal_state.json', {
        'closed': True,
        'record_sealed': True,
        'permanent_record_ref': 'seal-001',
    })
    _write('supervisory_incident_packet_evidence_bundle_state.json', {
        'packet_status': 'built',
        'last_packet_id': 'pkt-001',
    })
    _write('regulatory_inquiry_response_pack_state.json', {
        'inquiry_status': 'responded',
        'regulator': 'SEC',
        'open_inquiry_ref': 'SEC-2024-001',
        'last_dispatch_id': 'DISP-abc123',
    })
    _write('event_state_consistency_exception_queue.json', {'open_breaks': [], 'closed_breaks': []})
    _write('exception_escalation_trading_hold_state.json', {'hold_status': 'clear'})


def test_qntreal02m_full_lifecycle():
    client.post('/external-auditor-evidence/reset')
    _seed_happy_path()

    init = client.post('/external-auditor-evidence/initiate', json={
        'auditor_firm': 'Deloitte',
        'auditor_ref': 'DEL-2024-Q3',
        'audit_scope': 'full_supervisory_chain',
        'actor': 'tester',
    })
    assert init.status_code == 200
    ib = init.json()
    assert ib['initiated'] is True
    eng_id = ib['engagement_id']

    mapped = client.post('/external-auditor-evidence/map-evidence', json={'engagement_id': eng_id, 'actor': 'tester'})
    assert mapped.status_code == 200
    mb = mapped.json()
    assert mb['mapped'] is True
    assert mb['artifact_count'] >= 3

    pkg = client.post('/external-auditor-evidence/package', json={'engagement_id': eng_id, 'actor': 'tester'})
    assert pkg.status_code == 200
    pb = pkg.json()
    assert pb['packaged'] is True
    package_id = pb['package_id']

    ack = client.post('/external-auditor-evidence/acknowledge', json={
        'engagement_id': eng_id,
        'auditor_ack_ref': 'DEL-ACK-001',
        'actor': 'tester',
    })
    assert ack.status_code == 200
    ab = ack.json()
    assert ab['acknowledged'] is True

    cl = client.post('/external-auditor-evidence/close', json={'engagement_id': eng_id, 'actor': 'tester'})
    assert cl.status_code == 200
    cb = cl.json()
    assert cb['closed'] is True

    mod = verify_integrity()
    assert mod['mission'] == 'QNT-REAL02M'
    assert mod['audit_status'] == 'closed'


def test_qntreal02m_blocks_without_integrity():
    client.post('/external-auditor-evidence/reset')
    _write('supervisory_audit_trail_integrity_verification_state.json', {'integrity_ok': False, 'integrity_sealed': False})
    _write('supervisory_archive_retrieval_index_state.json', {'retrieval_ready': False, 'records': []})
    _write('supervisory_incident_closure_permanent_record_seal_state.json', {'closed': False, 'record_sealed': False})
    _write('supervisory_incident_packet_evidence_bundle_state.json', {'packet_status': 'idle'})
    _write('regulatory_inquiry_response_pack_state.json', {'inquiry_status': 'idle'})
    _write('event_state_consistency_exception_queue.json', {'open_breaks': [], 'closed_breaks': []})
    _write('exception_escalation_trading_hold_state.json', {'hold_status': 'clear'})

    resp = client.post('/external-auditor-evidence/initiate', json={
        'auditor_firm': 'PwC', 'auditor_ref': 'PWC-001', 'actor': 'tester'
    })
    body = resp.json()
    assert body['initiated'] is False or body.get('status') == 'blocked'
