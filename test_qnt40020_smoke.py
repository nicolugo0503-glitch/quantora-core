import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40017_independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_router as q17
from backend.app import qnt40018_administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_router as q18
from backend.app import qnt40019_pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer_router as q19
from backend.app import qnt40020_valuation_committee_minutes_challenge_resolution_evidence_final_nav_governance_record_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Final NAV Governor", "operator_id": "op_qnt40020", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Final NAV Governor"}
# seed dependent layers
q17.bootstrap_demo(user)
q18.bootstrap_demo(user)
q19.bootstrap_demo(user)
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["valuation_committee_minutes_challenge_resolution_evidence_final_nav_governance_record_layer_status"]
assert status["run_count"] >= 1
assert status["minutes_count"] >= 1
assert status["challenge_resolution_evidence_count"] >= 1
assert status["final_nav_governance_record_count"] >= 1
assert status["posture"] in {"FINAL_NAV_GOVERNANCE_STRONG", "FINAL_NAV_GOVERNANCE_CLEAR", "FINAL_NAV_GOVERNANCE_WATCH", "FINAL_NAV_GOVERNANCE_REMEDIATION_REQUIRED"}
print(json.dumps({"mission": "QNT40020", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
