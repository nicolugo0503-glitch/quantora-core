import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from modules.qnt_real02k.integrity import verify_integrity


client = TestClient(app)
ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / 'backend' / 'app' / 'state'


def _write(name, data):
    (STATE_DIR / name).write_text(json.dumps(data), encoding='utf-8')


def _seed_happy_path():
    _write('live_fill_event_stream_events.json', {
        'mission': 'QNT-REAL02A',
        'seen_event_ids': ['evt-1'],
        'events': [
            {
                'event_id': 'evt-1',
                'order_id': 'ORD-1',
                'broker': 'binance',
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'filled_qty': 1.0,
                'fill_price': 50000,
                'executed_at': 100,
                'ingested_at': 101,
            }
        ],
    })
    _write('execution_ledger_final_authority_state.json', {
        'history': [
            {'recorded_at': 102, 'order_id': 'ORD-1', 'lifecycle_stage': 'filled', 'filled_qty': 1.0},
        ]
    })
    _write('broker_order_status_timeline.json', {
        'mission': 'QNT-REAL02B',
        'seen_event_ids': [],
        'timelines': {
            'ORD-1': {
                'order_id': 'ORD-1',
                'current_state': 'filled',
                'terminal': True,
                'updated_at': 110,
                'transitions': [{'event_id': 'ord-evt-1', 'at': 110, 'from': 'accepted', 'to': 'filled', 'state': 'filled'}],
            }
        },
    })
    _write('event_state_consistency_exception_queue.json', {'open_breaks': [{'break_id': 'b1', 'order_id': 'ORD-1', 'severity': 'high', 'created_at': 120}], 'closed_breaks': []})
    _write('exception_escalation_trading_hold_state.json', {'hold_status': 'hold', 'escalation_status': 'hold', 'history': [{'event_id': 'hold-1', 'action': 'place_hold', 'hold_status': 'hold', 'at': 130}]})
    _write('supervisory_hold_release_certification_state.json', {'release_status': 'certified', 'hold_release_allowed': True, 'release_certified': True, 'history': [{'event_id': 'rel-1', 'action': 'release_certified', 'release_status': 'certified', 'release_certified': True, 'at': 140}]})
    _write('supervisory_incident_closure_permanent_record_seal_state.json', {'closed': True, 'record_sealed': True, 'permanent_record_ref': 'seal-001', 'history': [{'event_id': 'close-1', 'action': 'close', 'record_ref': 'seal-001', 'record_sealed': True, 'at': 150}]})
    _write('supervisory_archive_retrieval_index_state.json', {'retrieval_ready': True, 'records': [{'record_ref': 'seal-001', 'packet_id': 'pkt-001', 'retrieval_key': 'archive-seal-001', 'indexed_at': 160}], 'last_record_ref': 'seal-001', 'last_packet_id': 'pkt-001'})
    _write('supervisory_incident_packet_evidence_bundle_state.json', {'packet_status': 'built', 'last_packet_id': 'pkt-001', 'incident_open': False})
    _write('supervisory_retrieval_packet_export_state.json', {'last_record_ref': 'seal-001'})


def test_qntreal02k_summary_attest_export_happy_path():
    client.post('/supervisory-audit-integrity/reset')
    _seed_happy_path()

    s = client.get('/supervisory-audit-integrity/summary')
    assert s.status_code == 200
    sb = s.json()
    assert sb['mission'] == 'QNT-REAL02K'
    assert sb['integrity_ok'] is True
    assert sb['issue_counts']['gaps'] == 0

    a = client.post('/supervisory-audit-integrity/attest', json={'actor': 'tester', 'reason': 'smoke'})
    assert a.status_code == 200
    ab = a.json()
    assert ab['status'] == 'ok'
    assert ab['attested'] is True

    e = client.post('/supervisory-audit-integrity/export', json={'actor': 'tester', 'target': 'audit'})
    assert e.status_code == 200
    eb = e.json()
    assert eb['status'] == 'ok'
    assert eb['exported'] is True

    mod = verify_integrity()
    assert mod['mission'] == 'QNT-REAL02K'
    assert mod['integrity_ok'] is True


def test_qntreal02k_detects_orphan_fill_gap():
    client.post('/supervisory-audit-integrity/reset')
    _write('live_fill_event_stream_events.json', {'mission': 'QNT-REAL02A', 'seen_event_ids': [], 'events': [{'event_id': 'evt-x', 'order_id': 'ORD-X', 'broker': 'binance', 'symbol': 'ETHUSDT', 'side': 'BUY', 'filled_qty': 1.0, 'fill_price': 2000, 'executed_at': 100}]})
    _write('execution_ledger_final_authority_state.json', {'history': []})
    _write('broker_order_status_timeline.json', {'mission': 'QNT-REAL02B', 'seen_event_ids': [], 'timelines': {}})
    _write('event_state_consistency_exception_queue.json', {'open_breaks': [], 'closed_breaks': []})
    _write('exception_escalation_trading_hold_state.json', {'hold_status': 'clear'})
    _write('supervisory_hold_release_certification_state.json', {'release_status': 'idle'})
    _write('supervisory_incident_closure_permanent_record_seal_state.json', {'closed': False, 'record_sealed': False})
    _write('supervisory_archive_retrieval_index_state.json', {'retrieval_ready': False, 'records': []})
    _write('supervisory_incident_packet_evidence_bundle_state.json', {'packet_status': 'idle', 'last_packet_id': None})
    _write('supervisory_retrieval_packet_export_state.json', {})

    s = client.get('/supervisory-audit-integrity/summary')
    body = s.json()
    assert body['integrity_ok'] is False
    assert body['issue_counts']['orphans'] >= 1 or body['issue_counts']['gaps'] >= 1
