import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40002_real_time_pnl_performance_attribution_investor_metrics_layer_router as mod

email = "operator@quantora.test"
app_main.save_session({
    "logged_in": True,
    "email": email,
    "display_name": "Quantora Operator",
    "operator_id": "op_qnt40002",
})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["real_time_pnl_performance_attribution_investor_metrics_layer_status"]
assert status["run_count"] >= 1
assert status["posture"] in {"INVESTOR_METRICS_CLEAR", "PERFORMANCE_WATCH", "PERFORMANCE_REMEDIATION_REQUIRED"}
print(json.dumps({
    "mission": "QNT40002",
    "posture": status["posture"],
    "latest_score": status["latest_score"],
}, indent=2))
