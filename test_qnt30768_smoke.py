import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt30768_best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_router as mod

email = 'operator@quantora.test'
app_main.save_session({
    'logged_in': True,
    'email': email,
    'display_name': 'Quantora Operator',
    'operator_id': 'op_qnt30768',
})
user = {'email': email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res['ok'] is True
assert summary['best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_status']['run_count'] >= 1
assert summary['best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_status']['posture'] in {'MARKET_CONDUCT_ASSURANCE_CLEAR', 'EXECUTION_QUALITY_WATCH', 'EXECUTION_CONDUCT_REMEDIATION_REQUIRED'}
print(json.dumps({
    'mission': 'QNT30768',
    'posture': summary['best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_status']['posture'],
    'latest_score': summary['best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_status']['latest_score'],
}, indent=2))
