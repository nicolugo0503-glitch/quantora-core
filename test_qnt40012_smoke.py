import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40012_dealing_day_lock_nav_cutoff_enforcement_investor_transaction_freeze_control_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40012", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["dealing_day_lock_nav_cutoff_enforcement_investor_transaction_freeze_control_layer_status"]
assert status["run_count"] >= 1
assert status["lock_event_count"] >= 1
assert status["nav_cutoff_event_count"] >= 1
assert status["transaction_freeze_event_count"] >= 1
assert status["posture"] in {"TRANSACTION_FREEZE_CLEAR", "TRANSACTION_FREEZE_WATCH", "TRANSACTION_FREEZE_REMEDIATION_REQUIRED", "DEALING_DAY_LOCKED"}
print(json.dumps({"mission": "QNT40012", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
