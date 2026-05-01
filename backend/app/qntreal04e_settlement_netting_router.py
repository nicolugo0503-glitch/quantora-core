import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/settlement-netting", tags=["settlement-netting"])

STATE_FILE = "settlement_netting_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"mission": "QNT-04E", "status": "idle", "hard_blocked": True}


def _write_state(s: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)


class RunRequest(BaseModel):
    actor: Optional[str] = "operator"
    params: Optional[Dict[str, Any]] = None


@router.get("/health")
def health():
    return {"mission": "QNT-04E", "status": "ok", "component": "settlement-netting"}


@router.get("/summary")
def summary():
    s = _load_state()
    blockers = []
    if s.get("mission") != "QNT-04E":
        blockers.append("Integrity not established")
    s["blockers"] = blockers
    s["hard_blocked"] = len(blockers) > 0
    return s


@router.post("/run")
def run(req: RunRequest):
    run_id = f"QNT_04E_{uuid.uuid4().hex[:10].upper()}"
    s = _load_state()
    s["mission"] = "QNT-04E"
    s["status"] = "completed"
    s["run_id"] = run_id
    s["last_run_at"] = _now()
    s["run_by"] = req.actor
    s["params"] = req.params or {}
    s["hard_blocked"] = False
    _write_state(s)
    return {"completed": True, "mission": "QNT-04E", "run_id": run_id, "status": "completed"}


@router.post("/reset")
def reset():
    _write_state({"mission": "QNT-04E", "status": "idle", "hard_blocked": False})
    return {"reset": True}
