import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40032_supervisory_preservation_order_register_archive_chain_of_custody_audit_governance_record_access_challenge_resolution_layer_router as depa
from backend.app import qnt40033_supervisory_record_production_register_access_determination_review_governance_archive_disclosure_control_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Mission Governor", "operator_id": "op_qnt40033", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Mission Governor"}
depa.bootstrap_demo(user)
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["supervisory_record_production_register_access_determination_review_governance_archive_disclosure_control_layer_status"]
assert status["run_count"] >= 1
print(json.dumps({"mission": "QNT40033", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
