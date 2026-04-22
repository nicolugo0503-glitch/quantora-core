import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "backend" / "app" / "state" / "external_auditor_evidence_map_state.json"


def verify_integrity():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"mission": "QNT-REAL02M", "audit_status": "idle", "hard_blocked": True}
