import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40022_audit_opinion_readiness_open_item_clearance_financial_statement_release_authorization_layer_router as depa
from backend.app import qnt40015_investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_router as depb
from backend.app import qnt40023_financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Mission Governor", "operator_id": "op_qnt40023", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Mission Governor"}
depa.bootstrap_demo(user)
try:
    depb.bootstrap_demo(user)
except Exception:
    pass
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer_status"]
assert status["run_count"] >= 1
print(json.dumps({"mission": "QNT40023", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
