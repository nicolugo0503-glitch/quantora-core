import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "backend" / "app" / "state" / "regulatory_inquiry_response_pack_state.json"


def verify_integrity():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"mission": "QNT-REAL02L", "inquiry_status": "idle", "hard_blocked": True}
