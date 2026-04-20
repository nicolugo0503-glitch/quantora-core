import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt30769_cross_market_transaction_reporting_regulatory_disclosure_layer_router as mod

email = 'operator@quantora.test'
app_main.save_session({
    'logged_in': True,
    'email': email,
    'display_name': 'Quantora Operator',
    'operator_id': 'op_qnt30769',
})
user = {'email': email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res['ok'] is True
assert summary['cross_market_transaction_reporting_regulatory_disclosure_layer_status']['run_count'] >= 1
assert summary['cross_market_transaction_reporting_regulatory_disclosure_layer_status']['posture'] in {'REPORTING_AND_DISCLOSURE_CLEAR', 'REPORTING_WATCH', 'DISCLOSURE_REMEDIATION_REQUIRED'}
print(json.dumps({
    'mission': 'QNT30769',
    'posture': summary['cross_market_transaction_reporting_regulatory_disclosure_layer_status']['posture'],
    'latest_score': summary['cross_market_transaction_reporting_regulatory_disclosure_layer_status']['latest_score'],
}, indent=2))
