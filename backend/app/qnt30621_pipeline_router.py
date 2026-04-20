from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-opportunity-pipeline"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
PIPE_DIR = ARTIFACTS_DIR / "investor_opportunity_pipeline"

DEFAULT_STAGES = [
    "sourced",
    "meeting_scheduled",
    "dd_in_progress",
    "term_discussion",
    "soft_commit",
    "committed",
    "closed_lost",
]

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _crm():
    from backend.app import qnt30620_crm_router as crm
    return crm

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    PIPE_DIR.mkdir(parents=True, exist_ok=True)
    return PIPE_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "opportunities": [],
            "milestones": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    return json.loads(p.read_text(encoding="utf-8"))

def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2), encoding="utf-8")
    return d

def _find_opportunity(data, opportunity_id):
    return next((o for o in data.get("opportunities", []) if o.get("opportunity_id") == opportunity_id), None)

@router.get("/api/pipeline")
def pipeline():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/pipeline/opportunity")
def create_opportunity(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    item = {
        "opportunity_id": f"opp_{int(time.time())}",
        "investor_id": str(payload.get("investor_id") or ""),
        "opportunity_name": str(payload.get("opportunity_name") or "Capital Raise Opportunity"),
        "stage": str(payload.get("stage") or "sourced"),
        "target_amount": round(float(payload.get("target_amount") or 0.0), 2),
        "probability": int(payload.get("probability") or 0),
        "expected_close_date": str(payload.get("expected_close_date") or ""),
        "owner": str(payload.get("owner") or "Unassigned"),
        "source_channel": str(payload.get("source_channel") or ""),
        "notes": str(payload.get("notes") or ""),
        "status": "open",
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }
    data.setdefault("opportunities", []).insert(0, item)
    data["opportunities"] = data.get("opportunities", [])[:1000]
    _save(email, data)
    return {"status": "created", "opportunity": item}

@router.post("/api/pipeline/stage")
def update_stage(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    opportunity_id = str(payload.get("opportunity_id") or "")
    data = _load(email)
    opp = _find_opportunity(data, opportunity_id)
    if not opp:
        return {"status": "not_found"}
    if payload.get("stage") is not None:
        opp["stage"] = str(payload.get("stage"))
    if payload.get("probability") is not None:
        opp["probability"] = int(payload.get("probability"))
    if payload.get("target_amount") is not None:
        opp["target_amount"] = round(float(payload.get("target_amount")), 2)
    if payload.get("expected_close_date") is not None:
        opp["expected_close_date"] = str(payload.get("expected_close_date"))
    if payload.get("status") is not None:
        opp["status"] = str(payload.get("status"))
    opp["updated_at"] = int(time.time())
    _save(email, data)
    return {"status": "updated", "opportunity": opp}

@router.post("/api/pipeline/milestone")
def add_milestone(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    opportunity_id = str(payload.get("opportunity_id") or "")
    opp = _find_opportunity(data, opportunity_id)
    if not opp:
        return {"status": "opportunity_not_found"}
    item = {
        "milestone_id": f"mile_{int(time.time())}",
        "opportunity_id": opportunity_id,
        "investor_id": opp.get("investor_id"),
        "title": str(payload.get("title") or "Milestone"),
        "detail": str(payload.get("detail") or ""),
        "milestone_type": str(payload.get("milestone_type") or "general"),
        "created_at": int(time.time())
    }
    data.setdefault("milestones", []).insert(0, item)
    data["milestones"] = data.get("milestones", [])[:2000]
    _save(email, data)
    return {"status": "logged", "milestone": item}

@router.get("/api/pipeline/summary")
def pipeline_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    opportunities = data.get("opportunities", [])
    milestones = data.get("milestones", [])

    stage_counts = {stage: 0 for stage in DEFAULT_STAGES}
    for o in opportunities:
        stage = o.get("stage") or "unknown"
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    open_count = sum(1 for o in opportunities if o.get("status") == "open")
    committed_count = sum(1 for o in opportunities if o.get("stage") == "committed")
    weighted_pipeline = round(sum(float(o.get("target_amount") or 0.0) * (float(o.get("probability") or 0.0) / 100.0) for o in opportunities if o.get("status") == "open"), 2)
    total_target = round(sum(float(o.get("target_amount") or 0.0) for o in opportunities if o.get("status") == "open"), 2)

    latest_opportunity = opportunities[0] if opportunities else None
    latest_milestone = milestones[0] if milestones else None

    return {
        "email": email,
        "opportunity_count": len(opportunities),
        "milestone_count": len(milestones),
        "open_count": open_count,
        "committed_count": committed_count,
        "total_target_amount": total_target,
        "weighted_pipeline_amount": weighted_pipeline,
        "stage_counts": stage_counts,
        "latest_opportunity": latest_opportunity,
        "latest_milestone": latest_milestone,
        "opportunities": opportunities[:100],
        "milestones": milestones[:100]
    }
