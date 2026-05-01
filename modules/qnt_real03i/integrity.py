import json
import os

STATE_FILE = "model_risk_governance_state.json"

def check_integrity() -> dict:
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    ok = state.get("mission") == "QNT-REAL03I"
    return {
        "mission": "QNT-REAL03I",
        "integrity_ok": ok,
        "hard_blocked": not ok,
        "state_file": STATE_FILE,
        "status": state.get("status", "idle"),
    }
