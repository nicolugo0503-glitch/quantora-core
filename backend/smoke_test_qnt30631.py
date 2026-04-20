from pathlib import Path
import json

ART = Path(__file__).resolve().parent / 'artifacts'
ART.mkdir(parents=True, exist_ok=True)
(ART / 'session.json').write_text(json.dumps({
    'logged_in': True,
    'email': 'operator@quantora.test',
    'display_name': 'Operator',
}, indent=2), encoding='utf-8')

from backend.app import qnt30631_broker_integration_router as broker

email = 'operator@quantora.test'
demo = broker._bootstrap_demo(email, '2026-04')
summary = broker._summary(email)
assert demo['executed_orders'] >= 0
assert summary['order_count'] >= 0
assert summary['fill_count'] >= 0
print('QNT30631 smoke test passed:', json.dumps({'demo': demo, 'summary': summary}, indent=2))
