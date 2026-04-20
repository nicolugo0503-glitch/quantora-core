from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["capital-allocation-ledger"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
LEDGER_DIR = ARTIFACTS_DIR / "investor_capital_ledger"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _onboarding():
    from backend.app import qnt30623_onboarding_router as onboarding
    return onboarding

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email: str) -> Path:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    return LEDGER_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "accounts": [],
            "entries": [],
            "allocations": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    return json.loads(p.read_text(encoding="utf-8"))

def _save(email: str, d: dict) -> dict:
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2), encoding="utf-8")
    return d

def _find_account(data: dict, investor_id: str):
    return next((a for a in data.get("accounts", []) if a.get("investor_id") == investor_id), None)

def _find_allocation(data: dict, allocation_id: str):
    return next((a for a in data.get("allocations", []) if a.get("allocation_id") == allocation_id), None)

def _account_balance(entries, investor_id: str) -> float:
    total = 0.0
    for e in entries:
        if e.get("investor_id") == investor_id:
            total += float(e.get("amount") or 0.0)
    return round(total, 2)

@router.get("/api/capital-ledger")
def capital_ledger():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/capital-ledger/account")
def create_account(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    investor_id = str(payload.get("investor_id") or "")
    data = _load(email)

    if not investor_id:
        return {"status": "investor_id_required"}

    existing = _find_account(data, investor_id)
    if existing:
        return {"status": "exists", "account": existing}

    onboarding_data = _onboarding()._load(email)
    investor = next((i for i in onboarding_data.get("investors", []) if i.get("investor_id") == investor_id), None)

    item = {
        "account_id": f"acct_{int(time.time())}",
        "investor_id": investor_id,
        "investor_name": (investor or {}).get("name", "Investor"),
        "status": "open",
        "committed_capital": round(float((investor or {}).get("commitment") or payload.get("committed_capital") or 0.0), 2),
        "funded_capital": 0.0,
        "unfunded_capital": round(float((investor or {}).get("commitment") or payload.get("committed_capital") or 0.0), 2),
        "nav": 0.0,
        "ownership_pct": 0.0,
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }
    data.setdefault("accounts", []).insert(0, item)
    data["accounts"] = data.get("accounts", [])[:1000]
    _save(email, data)
    return {"status": "created", "account": item}

@router.post("/api/capital-ledger/entry")
def add_entry(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    investor_id = str(payload.get("investor_id") or "")
    data = _load(email)
    account = _find_account(data, investor_id)
    if not account:
        return {"status": "account_not_found"}

    amount = round(float(payload.get("amount") or 0.0), 2)
    entry_type = str(payload.get("entry_type") or "funding")
    if entry_type in {"withdrawal", "fee", "loss"} and amount > 0:
        amount = -amount

    entry = {
        "entry_id": f"entry_{int(time.time())}",
        "investor_id": investor_id,
        "account_id": account.get("account_id"),
        "entry_type": entry_type,
        "amount": amount,
        "description": str(payload.get("description") or ""),
        "created_at": int(time.time())
    }
    data.setdefault("entries", []).insert(0, entry)
    data["entries"] = data.get("entries", [])[:5000]

    funded = _account_balance(data.get("entries", []), investor_id)
    account["funded_capital"] = funded
    account["unfunded_capital"] = round(float(account.get("committed_capital") or 0.0) - funded, 2)
    account["nav"] = round(funded, 2)
    account["updated_at"] = int(time.time())

    _save(email, data)
    return {"status": "logged", "entry": entry, "account": account}

@router.post("/api/capital-ledger/allocation")
def allocate_capital(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    investor_id = str(payload.get("investor_id") or "")
    data = _load(email)
    account = _find_account(data, investor_id)
    if not account:
        return {"status": "account_not_found"}

    allocation = {
        "allocation_id": f"alloc_{int(time.time())}",
        "investor_id": investor_id,
        "strategy": str(payload.get("strategy") or "core"),
        "sleeve": str(payload.get("sleeve") or "main"),
        "amount": round(float(payload.get("amount") or 0.0), 2),
        "status": "active",
        "created_at": int(time.time())
    }
    data.setdefault("allocations", []).insert(0, allocation)
    data["allocations"] = data.get("allocations", [])[:3000]
    _save(email, data)
    return {"status": "allocated", "allocation": allocation}

@router.post("/api/capital-ledger/recalculate")
def recalculate():
    session = _require_user()
    email = session.get("email")
    data = _load(email)

    total_nav = 0.0
    for account in data.get("accounts", []):
        funded = _account_balance(data.get("entries", []), account.get("investor_id"))
        account["funded_capital"] = funded
        account["unfunded_capital"] = round(float(account.get("committed_capital") or 0.0) - funded, 2)
        account["nav"] = round(funded, 2)
        account["updated_at"] = int(time.time())
        total_nav += float(account.get("nav") or 0.0)

    total_nav = round(total_nav, 2)
    for account in data.get("accounts", []):
        nav = float(account.get("nav") or 0.0)
        account["ownership_pct"] = round((nav / total_nav * 100.0), 6) if total_nav > 0 else 0.0

    _save(email, data)
    return {"status": "recalculated", "total_nav": total_nav, "account_count": len(data.get("accounts", []))}

@router.get("/api/capital-ledger/summary")
def capital_ledger_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)

    total_committed = round(sum(float(a.get("committed_capital") or 0.0) for a in data.get("accounts", [])), 2)
    total_funded = round(sum(float(a.get("funded_capital") or 0.0) for a in data.get("accounts", [])), 2)
    total_unfunded = round(sum(float(a.get("unfunded_capital") or 0.0) for a in data.get("accounts", [])), 2)
    total_nav = round(sum(float(a.get("nav") or 0.0) for a in data.get("accounts", [])), 2)

    latest_account = data.get("accounts", [None])[0] if data.get("accounts") else None
    latest_entry = data.get("entries", [None])[0] if data.get("entries") else None
    latest_allocation = data.get("allocations", [None])[0] if data.get("allocations") else None

    return {
        "email": email,
        "account_count": len(data.get("accounts", [])),
        "entry_count": len(data.get("entries", [])),
        "allocation_count": len(data.get("allocations", [])),
        "total_committed_capital": total_committed,
        "total_funded_capital": total_funded,
        "total_unfunded_capital": total_unfunded,
        "total_nav": total_nav,
        "latest_account": latest_account,
        "latest_entry": latest_entry,
        "latest_allocation": latest_allocation,
        "accounts": data.get("accounts", [])[:100],
        "entries": data.get("entries", [])[:100],
        "allocations": data.get("allocations", [])[:100]
    }
