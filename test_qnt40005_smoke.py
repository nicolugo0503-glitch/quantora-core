import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40005_investor_aml_accreditation_suitability_admission_approval_layer_router as mod

email = "operator@quantora.test"
app_main.save_session({
    "logged_in": True,
    "email": email,
    "display_name": "Quantora Operator",
    "operator_id": "op_qnt40005",
    "is_admin": True,
})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["investor_aml_accreditation_suitability_admission_approval_layer_status"]
assert status["run_count"] >= 1
assert status["admission_decision_count"] >= 1
assert status["posture"] in {"ADMISSION_APPROVAL_CLEAR", "ADMISSION_WATCH", "ADMISSION_REMEDIATION_REQUIRED"}
print(json.dumps({
    "mission": "QNT40005",
    "posture": status["posture"],
    "latest_score": status["latest_score"],
}, indent=2))
