import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40010_redemption_queue_liquidity_gating_side_pocket_withdrawal_waterfall_control_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40010", "is_admin": True})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["redemption_queue_liquidity_gating_side_pocket_withdrawal_waterfall_control_layer_status"]
assert status["run_count"] >= 1
assert status["redemption_request_event_count"] >= 1
assert status["liquidity_gate_event_count"] >= 1
assert status["side_pocket_event_count"] >= 1
assert status["withdrawal_waterfall_event_count"] >= 1
assert status["posture"] in {"REDEMPTION_CONTROL_CLEAR", "REDEMPTION_CONTROL_WATCH", "REDEMPTION_CONTROL_REMEDIATION_REQUIRED", "INSTITUTIONAL_LIQUIDITY_LOCKED"}
print(json.dumps({"mission": "QNT40010", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
