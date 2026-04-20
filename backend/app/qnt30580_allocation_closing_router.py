from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["allocation-closing"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ALLOC_DIR = ARTIFACTS_DIR / "investor_allocation_commitments"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    ALLOC_DIR.mkdir(parents=True, exist_ok=True)
    return ALLOC_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "commitments": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

@router.get("/api/allocation-commitments")
def allocation_commitments():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/allocation-commitments/create")
def allocation_commitment_create(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    amount = round(float(payload.get("amount") or 0.0), 2)
    if not email or amount <= 0:
        raise HTTPException(status_code=400, detail="email and positive amount required")
    data = _load(email)
    item = {
        "commitment_id": f"alloc_{int(time.time())}",
        "title": (payload.get("title") or "Investor Allocation Commitment").strip(),
        "amount": amount,
        "currency": "USD",
        "status": "committed",
        "committed_at": int(time.time()),
        "closed_at": None,
        "notes": (payload.get("notes") or "").strip(),
    }
    data.setdefault("commitments", []).insert(0, item)
    data["commitments"] = data["commitments"][:100]
    _save(email, data)
    return {"status": "committed", "commitment": item}

@router.post("/api/allocation-commitments/close")
def allocation_commitment_close(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    commitment_id = payload.get("commitment_id")
    data = _load(email)
    item = next((c for c in data.get("commitments", []) if c.get("commitment_id") == commitment_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="commitment not found")
    item["status"] = "closed"
    item["closed_at"] = int(time.time())
    if payload.get("notes"):
        item["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "closed", "commitment": item}

@router.get("/api/allocation-commitments/summary")
def allocation_commitment_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    items = data.get("commitments", [])
    committed = sum(1 for x in items if x.get("status") == "committed")
    closed = sum(1 for x in items if x.get("status") == "closed")
    total = round(sum(float(x.get("amount") or 0.0) for x in items), 2)
    closed_total = round(sum(float(x.get("amount") or 0.0) for x in items if x.get("status") == "closed"), 2)
    return {
        "email": email,
        "total_commitments": len(items),
        "committed_items": committed,
        "closed_items": closed,
        "total_amount": total,
        "closed_amount": closed_total,
        "commitments": items,
    }
