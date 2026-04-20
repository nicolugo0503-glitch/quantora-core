import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40019_pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Valuation Source Admin", "operator_id": "op_qnt40019", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Valuation Source Admin"}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer_status"]
assert status["run_count"] >= 1
assert status["pricing_source_hierarchy_count"] >= 1
assert status["stale_price_exception_count"] >= 1
assert status["valuation_source_override_count"] >= 1
assert status["posture"] in {"SOURCE_GOVERNANCE_STRONG", "SOURCE_GOVERNANCE_CLEAR", "SOURCE_GOVERNANCE_WATCH", "SOURCE_GOVERNANCE_REMEDIATION_REQUIRED"}
print(json.dumps({"mission": "QNT40019", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
