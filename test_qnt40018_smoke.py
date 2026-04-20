import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40018_administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Admin Oversight", "operator_id": "op_qnt40018", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Admin Oversight"}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_status"]
assert status["run_count"] >= 1
assert status["administrator_shadow_nav_count"] >= 1
assert status["independent_nav_recalculation_count"] >= 1
assert status["nav_break_escalation_count"] >= 1
assert status["posture"] in {"NAV_BREAK_CONTROLLED", "NAV_CONTROL_CLEAR", "NAV_CONTROL_WATCH", "NAV_BREAK_REMEDIATION_REQUIRED"}
print(json.dumps({"mission": "QNT40018", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
