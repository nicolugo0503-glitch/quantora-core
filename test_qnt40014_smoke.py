import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40014_investor_nav_statement_finalization_delivery_acknowledgement_release_governance_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40014", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Operator"}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["investor_nav_statement_finalization_delivery_acknowledgement_release_governance_layer_status"]
assert status["run_count"] >= 1
assert status["nav_statement_finalization_count"] >= 1
assert status["delivery_acknowledgement_count"] >= 1
assert status["release_governance_action_count"] >= 1
assert status["posture"] in {"INVESTOR_RELEASE_CLEAR", "INVESTOR_RELEASE_WATCH", "INVESTOR_RELEASE_REMEDIATION_REQUIRED", "INVESTOR_RELEASE_GOVERNANCE_LOCKED"}
print(json.dumps({"mission": "QNT40014", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
