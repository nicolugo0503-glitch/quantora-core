import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from backend.app import main as app_main
from backend.app import qnt30772_regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_router as mod

email = "operator@quantora.test"
app_main.save_session({
    "logged_in": True,
    "email": email,
    "display_name": "Quantora Operator",
    "operator_id": "op_qnt30772",
})
user = {"email": email}
res = mod.bootstrap_demo(user)
summary = mod._summary_for_email(email)
assert res["ok"] is True
assert summary["regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_status"]["run_count"] >= 1
assert summary["regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_status"]["posture"] in {"COLLATERAL_PROTECTION_CLEAR", "COUNTERPARTY_WATCH", "COUNTERPARTY_REMEDIATION_REQUIRED"}
print(json.dumps({
    "mission": "QNT30772",
    "posture": summary["regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_status"]["posture"],
    "latest_score": summary["regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_status"]["latest_score"],
}, indent=2))
