import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40030_governance_archive_exception_review_retrieval_breach_escalation_supervisory_preservation_override_layer_router as depa
from backend.app import qnt40031_supervisory_archive_access_ledger_preservation_directive_tracking_governance_record_custody_assurance_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Mission Governor", "operator_id": "op_qnt40031", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Mission Governor"}
depa.bootstrap_demo(user)
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["supervisory_archive_access_ledger_preservation_directive_tracking_governance_record_custody_assurance_layer_status"]
assert status["run_count"] >= 1
print(json.dumps({"mission": "QNT40031", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
