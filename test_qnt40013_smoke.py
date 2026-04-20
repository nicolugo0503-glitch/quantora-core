import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40013_nav_publication_investor_notice_release_post_dealing_confirmation_distribution_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Operator", "operator_id": "op_qnt40013", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["nav_publication_investor_notice_release_post_dealing_confirmation_distribution_layer_status"]
assert status["run_count"] >= 1
assert status["nav_publication_count"] >= 1
assert status["investor_notice_release_count"] >= 1
assert status["confirmation_distribution_count"] >= 1
assert status["posture"] in {"POST_DEALING_NOTICE_CLEAR", "POST_DEALING_NOTICE_WATCH", "POST_DEALING_NOTICE_REMEDIATION_REQUIRED", "POST_DEALING_PUBLICATION_LOCKED"}
print(json.dumps({"mission": "QNT40013", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
