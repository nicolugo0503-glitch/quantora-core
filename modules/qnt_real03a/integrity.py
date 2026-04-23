import json
import os

STATE_FILE = "real03a_portfolio_stress_test_state.json"

def check_integrity() -> dict:
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    ok = state.get("mission") == "QNT-REAL03A"
    return {
        "mission": "QNT-REAL03A",
        "integrity_ok": ok,
        "hard_blocked": not ok,
        "state_file": STATE_FILE,
        "stress_test_status": state.get("stress_test_status", "idle"),
        "scenario_count": state.get("scenario_count", 0),
        "last_run_id": state.get("last_run_id"),
    }
