import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40015_investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40015", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Operator"}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_status"]
assert status["run_count"] >= 1
assert status["statement_consolidation_count"] >= 1
assert status["period_close_certification_count"] >= 1
assert status["lp_book_lock_count"] >= 1
assert status["posture"] in {"PERIOD_CLOSE_CLEAR", "PERIOD_CLOSE_WATCH", "PERIOD_CLOSE_REMEDIATION_REQUIRED", "LP_BOOK_FINAL_LOCKED"}
print(json.dumps({"mission": "QNT40015", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
