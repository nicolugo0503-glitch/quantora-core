import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from modules.qnt_real02l.integrity import verify_integrity


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
    _write('supervisory_retrieval_packet_export_state.json', {'last_record_ref': 'seal-001'})
    _write('event_state_consistency_exception_queue.json', {'open_breaks': [], 'closed_breaks': []})
    _write('exception_escalation_trading_hold_state.json', {'hold_status': 'clear'})


def test_qntreal02l_register_compose_certify_dispatch():
    client.post('/regulatory-inquiry-response/reset')
    _seed_happy_path()

    reg = client.post('/regulatory-inquiry-response/register', json={
        'regulator': 'SEC',
        'inquiry_type': 'enforcement_inquiry',
        'inquiry_subject': 'BTCUSDT fill discrepancy',
        'inquiry_ref': 'SEC-2024-001',
    })
    assert reg.status_code == 200
    rb = reg.json()
    assert rb['registered'] is True
    assert rb['regulator'] == 'SEC'

    comp = client.post('/regulatory-inquiry-response/compose', json={'actor': 'tester'})
    assert comp.status_code == 200
    cb = comp.json()
    assert cb['composed'] is True
    assert cb['section_count'] >= 4

    cert = client.post('/regulatory-inquiry-response/certify', json={'actor': 'tester', 'reason': 'smoke'})
    assert cert.status_code == 200
    certb = cert.json()
    assert certb['certified'] is True

    disp = client.post('/regulatory-inquiry-response/dispatch', json={'actor': 'tester', 'channel': 'secure-portal'})
    assert disp.status_code == 200
    db = disp.json()
    assert db['dispatched'] is True

    mod = verify_integrity()
    assert mod['mission'] == 'QNT-REAL02L'
    assert mod['inquiry_status'] == 'responded'


def test_qntreal02l_blocks_without_integrity():
    client.post('/regulatory-inquiry-response/reset')
    _write('supervisory_audit_trail_integrity_verification_state.json', {'integrity_ok': False, 'integrity_sealed': False})
    _write('supervisory_archive_retrieval_index_state.json', {'retrieval_ready': False, 'records': []})
    _write('supervisory_incident_closure_permanent_record_seal_state.json', {'closed': False, 'record_sealed': False})
    _write('supervisory_incident_packet_evidence_bundle_state.json', {'packet_status': 'idle'})
    _write('supervisory_retrieval_packet_export_state.json', {})
    _write('event_state_consistency_exception_queue.json', {'open_breaks': [], 'closed_breaks': []})
    _write('exception_escalation_trading_hold_state.json', {'hold_status': 'clear'})

    client.post('/regulatory-inquiry-response/register', json={'regulator': 'FINRA', 'inquiry_type': 'routine_exam'})
    comp = client.post('/regulatory-inquiry-response/compose', json={'actor': 'tester'})
    body = comp.json()
    assert body['composed'] is False or body.get('status') == 'blocked'
