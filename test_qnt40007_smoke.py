import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt40007_investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer_router as mod

email = "operator@quantora.test"
app_main.save_session({
    "logged_in": True,
    "email": email,
    "display_name": "Quantora Operator",
    "operator_id": "op_qnt40007",
    "is_admin": True,
})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
status = summary["investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer_status"]
assert status["run_count"] >= 1
assert status["funding_settlement_event_count"] >= 1
assert status["subscription_reconciliation_event_count"] >= 1
assert status["capital_receipt_finalization_event_count"] >= 1
assert status["posture"] in {"CAPITAL_RECEIPT_FINALIZATION_CLEAR", "RECEIPT_RECONCILIATION_WATCH", "RECEIPT_REMEDIATION_REQUIRED", "INSTITUTIONAL_RECEIPT_FINALIZED"}
print(json.dumps({
    "mission": "QNT40007",
    "posture": status["posture"],
    "latest_score": status["latest_score"],
}, indent=2))
