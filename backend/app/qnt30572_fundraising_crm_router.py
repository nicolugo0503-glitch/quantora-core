from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["fundraising-crm"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CRM_DIR = ARTIFACTS_DIR / "fundraising_crm_pipeline"

STAGES = ["lead", "contacted", "ddq", "soft_circle", "committed", "funded"]

def _main():
    from backend.app import main as app_main
    return app_main

def _path() -> Path:
    CRM_DIR.mkdir(parents=True, exist_ok=True)
    return CRM_DIR / "crm_pipeline.json"

def _load() -> dict:
    path = _path()
    if not path.exists():
        data = {"investors": [], "activity": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(data: dict) -> dict:
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _require_admin():
    return _main().require_admin()

def _find(data: dict, investor_id: str):
    return next((x for x in data.get("investors", []) if x.get("investor_id") == investor_id), None)

@router.get("/api/fundraising-crm/summary")
def fundraising_crm_summary():
    _require_admin()
    data = _load()
    investors = data.get("investors", [])
    stage_counts = {s: 0 for s in STAGES}
    total_target = 0.0
    total_committed = 0.0
    for inv in investors:
        stage = (inv.get("stage") or "lead").strip().lower()
        if stage in stage_counts:
            stage_counts[stage] += 1
        total_target += float(inv.get("target_allocation") or 0.0)
        total_committed += float(inv.get("committed_amount") or 0.0)
    return {
        "investor_count": len(investors),
        "stage_counts": stage_counts,
        "total_target_allocation": round(total_target, 2),
        "total_committed_amount": round(total_committed, 2),
        "activity_count": len(data.get("activity", [])),
        "investors": investors[:200],
    }

@router.get("/api/fundraising-crm/investors")
def fundraising_crm_investors():
    _require_admin()
    return _load()

@router.post("/api/fundraising-crm/investor")
def fundraising_crm_add_investor(payload: dict = Body(...)):
    _require_admin()
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    if not name or not email:
        raise HTTPException(status_code=400, detail="name and email required")
    data = _load()
    investor = {
        "investor_id": "inv_" + hashlib.sha256(f"{email}:{time.time()}".encode("utf-8")).hexdigest()[:16],
        "name": name,
        "email": email,
        "stage": (payload.get("stage") or "lead").strip().lower(),
        "type": (payload.get("type") or "allocator").strip().lower(),
        "target_allocation": round(float(payload.get("target_allocation") or 0.0), 2),
        "committed_amount": round(float(payload.get("committed_amount") or 0.0), 2),
        "notes": (payload.get("notes") or "").strip(),
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    data.setdefault("investors", []).insert(0, investor)
    data.setdefault("activity", []).insert(0, {"type": "investor_added", "investor_id": investor["investor_id"], "timestamp": int(time.time())})
    data["activity"] = data["activity"][:500]
    _save(data)
    return {"status": "added", "investor": investor}

@router.post("/api/fundraising-crm/stage")
def fundraising_crm_update_stage(payload: dict = Body(...)):
    _require_admin()
    data = _load()
    investor_id = payload.get("investor_id")
    stage = (payload.get("stage") or "").strip().lower()
    inv = _find(data, investor_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")
    if stage not in STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")
    inv["stage"] = stage
    inv["updated_at"] = int(time.time())
    data.setdefault("activity", []).insert(0, {"type": "stage_updated", "investor_id": investor_id, "stage": stage, "timestamp": int(time.time())})
    data["activity"] = data["activity"][:500]
    _save(data)
    return {"status": "updated", "investor": inv}

@router.post("/api/fundraising-crm/commitment")
def fundraising_crm_commitment(payload: dict = Body(...)):
    _require_admin()
    data = _load()
    investor_id = payload.get("investor_id")
    inv = _find(data, investor_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")
    inv["committed_amount"] = round(float(payload.get("committed_amount") or 0.0), 2)
    inv["updated_at"] = int(time.time())
    data.setdefault("activity", []).insert(0, {"type": "commitment_updated", "investor_id": investor_id, "committed_amount": inv["committed_amount"], "timestamp": int(time.time())})
    data["activity"] = data["activity"][:500]
    _save(data)
    return {"status": "updated", "investor": inv}

@router.post("/api/fundraising-crm/note")
def fundraising_crm_note(payload: dict = Body(...)):
    _require_admin()
    data = _load()
    investor_id = payload.get("investor_id")
    inv = _find(data, investor_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")
    note = (payload.get("note") or "").strip()
    inv["notes"] = ((inv.get("notes") or "") + "\n" + note).strip()
    inv["updated_at"] = int(time.time())
    data.setdefault("activity", []).insert(0, {"type": "note_added", "investor_id": investor_id, "timestamp": int(time.time())})
    data["activity"] = data["activity"][:500]
    _save(data)
    return {"status": "saved", "investor": inv}
