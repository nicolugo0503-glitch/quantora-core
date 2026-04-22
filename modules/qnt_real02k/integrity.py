import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "backend" / "app" / "state" / "supervisory_audit_trail_integrity_verification_state.json"


def verify_integrity():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"mission": "QNT-REAL02K", "verification_status": "idle", "integrity_ok": False}
