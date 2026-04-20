from pathlib import Path
import json

from backend.app import main as main_app
from backend.app import qnt30630_allocation_engine_router as alloc

ART = Path(__file__).resolve().parent / 'artifacts'
ART.mkdir(parents=True, exist_ok=True)
(ART / 'session.json').write_text(json.dumps({
    'logged_in': True,
    'email': 'operator@quantora.test',
    'display_name': 'Operator',
}, indent=2), encoding='utf-8')

email = 'operator@quantora.test'
alloc._statement()._seed_demo(email, '2026-04')
alloc._execution()._bootstrap_demo(email, '2026-04')
try:
    alloc._performance().performance_engine_bootstrap_demo({'months': 6})
except Exception:
    alloc._performance().performance_engine_snapshot({})
    alloc._performance().performance_engine_bootstrap_demo({'months': 6})

plan = alloc._build_plan(email, '2026-04')
assert plan['deployable_capital'] > 0
assert plan['eligible_strategy_count'] >= 1
assert len(plan['strategies']) >= 1

decision = alloc._persist_decision(email, plan, 'smoke test')
assert decision['deployable_capital'] == plan['deployable_capital']
assert decision['strategies']

print('QNT30630 smoke test passed')
