import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40034_supervisory_production_packet_assembly_governance_archive_release_approval_official_record_disclosure_ledger_layer_router as depa
from backend.app import qnt40035_supervisory_production_delivery_certification_record_disclosure_acknowledgement_archive_release_closure_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Mission Governor", "operator_id": "op_qnt40035", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Mission Governor"}
depa.bootstrap_demo(user)
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["supervisory_production_delivery_certification_record_disclosure_acknowledgement_archive_release_closure_layer_status"]
assert status["run_count"] >= 1
print(json.dumps({"mission": "QNT40035", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
