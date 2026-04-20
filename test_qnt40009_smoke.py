import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40009_fee_engine_management_fee_performance_fee_hwm_hurdle_rate_incentive_allocation_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40009", "is_admin": True})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["fee_engine_management_fee_performance_fee_hwm_hurdle_rate_incentive_allocation_layer_status"]
assert status["run_count"] >= 1
assert status["fee_term_event_count"] >= 1
assert status["fee_snapshot_event_count"] >= 1
assert status["fee_crystallization_event_count"] >= 1
assert status["incentive_allocation_event_count"] >= 1
assert status["posture"] in {"FEE_ENGINE_CLEAR", "FEE_ENGINE_WATCH", "FEE_ENGINE_REMEDIATION_REQUIRED", "INSTITUTIONAL_INCENTIVE_LOCKED"}
print(json.dumps({"mission": "QNT40009", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
