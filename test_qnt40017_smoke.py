import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40017_independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40017", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Operator"}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_status"]
assert status["run_count"] >= 1
assert status["independent_price_verification_count"] >= 1
assert status["valuation_committee_challenge_count"] >= 1
assert status["fair_value_override_count"] >= 1
assert status["posture"] in {"FAIR_VALUE_GOVERNED", "VALUATION_CLEAR", "VALUATION_WATCH", "VALUATION_REMEDIATION_REQUIRED"}
print(json.dumps({"mission": "QNT40017", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
