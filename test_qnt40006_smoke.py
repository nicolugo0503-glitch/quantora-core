import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40006_investor_commitments_subscription_acceptance_capital_call_scheduling_layer_router as mod

email = "operator@quantora.test"
app_main.save_session({
    "logged_in": True,
    "email": email,
    "display_name": "Quantora Operator",
    "operator_id": "op_qnt40006",
    "is_admin": True,
})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["investor_commitments_subscription_acceptance_capital_call_scheduling_layer_status"]
assert status["run_count"] >= 1
assert status["commitment_event_count"] >= 1
assert status["capital_call_schedule_event_count"] >= 1
assert status["posture"] in {"CAPITAL_CALL_SCHEDULING_CLEAR", "SCHEDULING_WATCH", "SCHEDULING_REMEDIATION_REQUIRED", "INSTITUTIONAL_CAPITAL_CALL_READY"}
print(json.dumps({
    "mission": "QNT40006",
    "posture": status["posture"],
    "latest_score": status["latest_score"],
}, indent=2))
