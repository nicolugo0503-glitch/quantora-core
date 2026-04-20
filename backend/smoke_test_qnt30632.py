from pathlib import Path
import json

ART = Path(__file__).resolve().parent / 'artifacts'
ART.mkdir(parents=True, exist_ok=True)
(ART / 'session.json').write_text(json.dumps({
    'logged_in': True,
    'email': 'operator@quantora.test',
    'display_name': 'Operator',
}, indent=2), encoding='utf-8')

from backend.app import qnt30632_autonomous_fund_router as auto

email = 'operator@quantora.test'
demo = auto._bootstrap_demo(email, '2026-04')
summary = auto._summary(email)
assert demo['executed_orders'] >= 0
assert summary['cycle_count'] >= 1
print('QNT30632 smoke test passed:', json.dumps({'demo': demo, 'cycle_count': summary['cycle_count']}, indent=2))
