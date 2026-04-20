import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40027_board_resolution_archive_committee_approval_trace_annual_governance_evidence_lock_layer_router as depa
from backend.app import qnt40026_board_reporting_agenda_control_annual_meeting_materials_approval_investor_communication_governance_lock_layer_router as depb
from backend.app import qnt40028_annual_governance_binder_assembly_board_certification_release_permanent_record_seal_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Mission Governor", "operator_id": "op_qnt40028", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Mission Governor"}
depa.bootstrap_demo(user)
try:
    depb.bootstrap_demo(user)
except Exception:
    pass
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["annual_governance_binder_assembly_board_certification_release_permanent_record_seal_layer_status"]
assert status["run_count"] >= 1
print(json.dumps({"mission": "QNT40028", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
