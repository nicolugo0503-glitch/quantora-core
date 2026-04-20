import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40011_redemption_settlement_in_kind_transfer_control_investor_exit_finalization_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40011", "is_admin": True})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["redemption_settlement_in_kind_transfer_control_investor_exit_finalization_layer_status"]
assert status["run_count"] >= 1
assert status["settlement_event_count"] >= 1
assert status["in_kind_transfer_event_count"] >= 1
assert status["exit_finalization_event_count"] >= 1
assert status["posture"] in {"EXIT_FINALIZATION_CLEAR", "EXIT_FINALIZATION_WATCH", "EXIT_FINALIZATION_REMEDIATION_REQUIRED", "INSTITUTIONAL_EXIT_LOCKED"}
print(json.dumps({"mission": "QNT40011", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
