import sys, json
from pathlib import Path
base = Path('/mnt/data/qnt30633_build')
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt30633_governance_compliance_router as gov

app_main.save_session({
    'logged_in': True,
    'email': 'operator@quantora.test',
    'display_name': 'Quantora Operator',
    'operator_id': 'op_qnt30633'
})

demo = gov._seed_demo('operator@quantora.test')
summary = gov._summary('operator@quantora.test')
eval_live = gov._evaluate_action('operator@quantora.test', {
    'action_type': 'broker_order',
    'strategy_id': 'MACRO_TREND',
    'symbol': 'AAPL',
    'target_weight': 0.20,
    'order_notional': 100000,
    'projected_drawdown_pct': 10,
    'execution_mode': 'live',
})
assert summary['audit_summary']['chain_integrity_ok'] is True
assert eval_live['status'] in {'requires_approval', 'requires_review', 'approved', 'blocked'}
print(json.dumps({
    'demo': demo,
    'open_approval_count': summary['open_approval_count'],
    'blocked_event_count': summary['blocked_event_count'],
    'audit_chain_ok': summary['audit_summary']['chain_integrity_ok'],
    'live_eval_status': eval_live['status'],
}, indent=2))
