import json
from pathlib import Path

from backend.app.regulatory_disclosure_delivery.engine import RegulatoryDisclosureDeliveryEngine


def first_published_binder_id() -> str:
    state = json.loads(Path('backend/app/state/governance_binder_publication_state.json').read_text())
    binders = state.get('published_binders') or []
    if not binders:
        raise RuntimeError('no published binders found in QNT50014 state for smoke test')
    return binders[0]['published_binder_id']


def main():
    engine = RegulatoryDisclosureDeliveryEngine()
    published_binder_id = first_published_binder_id()
    delivery = engine.register_delivery({
        'operator': 'smoke',
        'published_binder_id': published_binder_id,
        'operations': 'ops',
        'compliance': 'compliance',
        'supervisor': 'sec_desk',
    })
    case = delivery['delivery_case']
    receipt = engine.record_delivery_receipt({'delivery_case_id': case['delivery_case_id'], 'receiver': 'sec_gateway'})
    ack = engine.record_acknowledgement({'delivery_case_id': case['delivery_case_id'], 'acknowledger': 'sec_reviewer', 'outcome': 'accepted'})
    summary = engine.summary()
    assert case['status'] == 'pending_delivery_receipt'
    assert receipt['delivery_case']['status'] == 'delivered_pending_acknowledgement'
    assert ack['status'] == 'acknowledged'
    assert summary['supervisory_acknowledgement_count'] >= 1
    print('QNT50015 smoke passed')


if __name__ == '__main__':
    main()
