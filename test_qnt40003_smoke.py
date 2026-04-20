import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40003_investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer_router as mod

email = "operator@quantora.test"
app_main.save_session({
    "logged_in": True,
    "email": email,
    "display_name": "Quantora Operator",
    "operator_id": "op_qnt40003",
})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer_status"]
assert status["run_count"] >= 1
assert status["distribution_count"] >= 1
assert status["posture"] in {"LP_DISTRIBUTION_CLEAR", "LP_DISTRIBUTION_WATCH", "LP_DISTRIBUTION_REMEDIATION_REQUIRED"}
print(json.dumps({
    "mission": "QNT40003",
    "posture": status["posture"],
    "latest_score": status["latest_score"],
}, indent=2))
