import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40016_fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Controller", "operator_id": "op_qnt40016", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Controller"}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_status"]
assert status["run_count"] >= 1
assert status["nav_package_approval_count"] >= 1
assert status["controller_sign_off_count"] >= 1
assert status["official_books_release_count"] >= 1
assert status["posture"] in {"OFFICIAL_RELEASE_CLEAR", "OFFICIAL_RELEASE_WATCH", "OFFICIAL_RELEASE_REMEDIATION_REQUIRED", "OFFICIAL_BOOKS_RELEASED"}
print(json.dumps({"mission": "QNT40016", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
