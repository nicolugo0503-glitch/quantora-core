
from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["nav-registry"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
NAV_DIR = ARTIFACTS_DIR / "investor_nav_registry"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v:str)->str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email:str)->Path:
    NAV_DIR.mkdir(parents=True, exist_ok=True)
    return NAV_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email:str)->dict:
    p=_path(email)
    if not p.exists():
        d={"email":email,"allocations":[]}
        p.write_text(json.dumps(d,indent=2))
        return d
    return json.loads(p.read_text())

def _save(email,data):
    _path(email).write_text(json.dumps(data,indent=2))
    return data

@router.get("/api/nav-registry")
def nav_registry():
    s=_require_user()
    return _load(s.get("email"))

@router.post("/api/nav-registry/allocate")
def nav_allocate(payload:dict=Body(...)):
    _require_admin()
    email=payload.get("email")
    nav=float(payload.get("nav") or 0)
    if not email or nav<=0:
        raise HTTPException(400,"email and nav required")
    d=_load(email)
    item={
        "allocation_id":f"nav_{int(time.time())}",
        "nav":round(nav,2),
        "ownership_pct":float(payload.get("ownership_pct") or 0),
        "created_at":int(time.time())
    }
    d.setdefault("allocations",[]).insert(0,item)
    _save(email,d)
    return {"status":"allocated","item":item}

@router.get("/api/nav-registry/summary")
def nav_summary():
    s=_require_user()
    email=s.get("email")
    d=_load(email)
    total=sum(x.get("nav",0) for x in d.get("allocations",[]))
    return {
        "email":email,
        "total_nav":round(total,2),
        "allocations":d.get("allocations",[])
    }
