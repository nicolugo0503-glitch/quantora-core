import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40008_investor_equalization_series_accounting_nav_entry_allocation_control_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40008", "is_admin": True})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["investor_equalization_series_accounting_nav_entry_allocation_control_layer_status"]
assert status["run_count"] >= 1
assert status["series_event_count"] >= 1
assert status["nav_entry_event_count"] >= 1
assert status["performance_allocation_event_count"] >= 1
assert status["equalization_adjustment_event_count"] >= 1
assert status["posture"] in {"NAV_ALLOCATION_CLEAR", "EQUALIZATION_WATCH", "EQUALIZATION_REMEDIATION_REQUIRED", "INSTITUTIONAL_NAV_ALLOCATION_LOCKED"}
print(json.dumps({"mission": "QNT40008", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
