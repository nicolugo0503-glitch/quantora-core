import json
import sys
from pathlib import Path
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt30748_institutional_external_auditor_interface_layer_router as q48
from backend.app import qnt40016_fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_router as q16
from backend.app import qnt40017_independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_router as q17
from backend.app import qnt40018_administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_router as q18
from backend.app import qnt40019_pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer_router as q19
from backend.app import qnt40020_valuation_committee_minutes_challenge_resolution_evidence_final_nav_governance_record_layer_router as q20
from backend.app import qnt40021_auditor_pbc_package_assembly_valuation_support_binder_final_nav_evidence_delivery_layer_router as q21
from backend.app import qnt40022_audit_opinion_readiness_open_item_clearance_financial_statement_release_authorization_layer_router as mod
email = "operator@quantora.test"
app_main.save_session({"logged_in": True, "email": email, "display_name": "Quantora Audit Release Governor", "operator_id": "op_qnt40022", "is_admin": True})
user = {"email": email, "logged_in": True, "is_admin": True, "display_name": "Quantora Audit Release Governor"}
q48.bootstrap_demo(user)
q16.bootstrap_demo(user)
q17.bootstrap_demo(user)
q18.bootstrap_demo(user)
q19.bootstrap_demo(user)
q20.bootstrap_demo(user)
q21.bootstrap_demo(user)
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["audit_opinion_readiness_open_item_clearance_financial_statement_release_authorization_layer_status"]
assert status["run_count"] >= 1
assert status["audit_opinion_readiness_review_count"] >= 1
assert status["open_item_clearance_count"] >= 1
assert status["financial_statement_release_authorization_count"] >= 1
assert status["posture"] in {"AUDIT_RELEASE_GOVERNANCE_STRONG", "AUDIT_RELEASE_GOVERNANCE_CLEAR", "AUDIT_RELEASE_GOVERNANCE_WATCH", "AUDIT_RELEASE_GOVERNANCE_REMEDIATION_REQUIRED"}
print(json.dumps({"mission": "QNT40022", "posture": status["posture"], "latest_score": status["latest_score"]}, indent=2))
