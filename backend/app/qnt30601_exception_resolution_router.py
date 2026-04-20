from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["reconciliation-exception-resolution"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
EXC_DIR = ARTIFACTS_DIR / "reconciliation_exception_resolution"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _recon():
    from backend.app import qnt30600_reconciliation_router as recon
    return recon

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    EXC_DIR.mkdir(parents=True, exist_ok=True)
    return EXC_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "exceptions": [],
            "history": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _find_exception(data: dict, exception_id: str):
    return next((e for e in data.get("exceptions", []) if e.get("exception_id") == exception_id), None)

def _latest_reconciliation_issues(email: str):
    recon_data = _recon()._load(email)
    runs = recon_data.get("runs") or []
    if not runs:
        run = _recon()._run_checks(email)
        recon_data.setdefault("runs", []).insert(0, run)
        _recon()._save(email, recon_data)
        return run.get("issues", [])
    return runs[0].get("issues", [])

@router.get("/api/reconciliation-exceptions")
def reconciliation_exceptions():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/reconciliation-exceptions/import-latest")
def reconciliation_exceptions_import_latest(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    issues = _latest_reconciliation_issues(email)
    data = _load(email)

    imported = []
    existing_codes = {(e.get("code"), e.get("message")) for e in data.get("exceptions", [])}
    for issue in issues:
        key = (issue.get("code"), issue.get("message"))
        if key in existing_codes:
            continue
        item = {
            "exception_id": f"exc_{int(time.time())}_{len(imported)+1}",
            "code": issue.get("code"),
            "severity": issue.get("severity"),
            "message": issue.get("message"),
            "difference": issue.get("difference"),
            "status": "open",
            "resolution_notes": "",
            "owner": "",
            "created_at": int(time.time()),
            "resolved_at": None,
        }
        data.setdefault("exceptions", []).insert(0, item)
        imported.append(item)
    data["exceptions"] = data["exceptions"][:500]
    if imported:
        data.setdefault("history", []).insert(0, {
            "type": "import_latest_reconciliation_issues",
            "count": len(imported),
            "timestamp": int(time.time()),
        })
    data["history"] = data.get("history", [])[:500]
    _save(email, data)
    return {"status": "imported", "imported_count": len(imported), "exceptions": imported}

@router.post("/api/reconciliation-exceptions/assign")
def reconciliation_exceptions_assign(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    exception_id = (payload.get("exception_id") or "").strip()
    owner = (payload.get("owner") or "").strip()
    if not email or not exception_id or not owner:
        raise HTTPException(status_code=400, detail="email, exception_id, owner required")
    data = _load(email)
    item = _find_exception(data, exception_id)
    if not item:
        raise HTTPException(status_code=404, detail="exception not found")
    item["owner"] = owner
    item["status"] = "in_review"
    data.setdefault("history", []).insert(0, {
        "type": "exception_assigned",
        "exception_id": exception_id,
        "owner": owner,
        "timestamp": int(time.time()),
    })
    data["history"] = data["history"][:500]
    _save(email, data)
    return {"status": "assigned", "exception": item}

@router.post("/api/reconciliation-exceptions/resolve")
def reconciliation_exceptions_resolve(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    exception_id = (payload.get("exception_id") or "").strip()
    if not exception_id:
        raise HTTPException(status_code=400, detail="exception_id required")
    data = _load(email)
    item = _find_exception(data, exception_id)
    if not item:
        raise HTTPException(status_code=404, detail="exception not found")
    item["status"] = "resolved"
    item["resolved_at"] = int(time.time())
    item["resolution_notes"] = str(payload.get("resolution_notes") or "")
    data.setdefault("history", []).insert(0, {
        "type": "exception_resolved",
        "exception_id": exception_id,
        "timestamp": int(time.time()),
    })
    data["history"] = data["history"][:500]
    _save(email, data)
    return {"status": "resolved", "exception": item}

@router.get("/api/reconciliation-exceptions/summary")
def reconciliation_exceptions_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    exceptions = data.get("exceptions", [])
    open_count = sum(1 for e in exceptions if e.get("status") == "open")
    in_review_count = sum(1 for e in exceptions if e.get("status") == "in_review")
    resolved_count = sum(1 for e in exceptions if e.get("status") == "resolved")
    high_count = sum(1 for e in exceptions if e.get("severity") == "high")
    latest = exceptions[0] if exceptions else None
    return {
        "email": email,
        "exception_count": len(exceptions),
        "open_count": open_count,
        "in_review_count": in_review_count,
        "resolved_count": resolved_count,
        "high_severity_count": high_count,
        "latest_exception": latest,
        "exceptions": exceptions[:100],
        "history": data.get("history", [])[:100],
    }
