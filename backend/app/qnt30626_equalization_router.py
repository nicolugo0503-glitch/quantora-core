from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["equalization-series-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
EQ_DIR = ARTIFACTS_DIR / "equalization_series_engine"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email: str) -> Path:
    EQ_DIR.mkdir(parents=True, exist_ok=True)
    return EQ_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "share_classes": [],
            "series_accounts": [],
            "equalization_events": [],
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

def _find_class(data: dict, share_class_id: str):
    return next((c for c in data.get("share_classes", []) if c.get("share_class_id") == share_class_id), None)

def _find_series(data: dict, series_id: str):
    return next((s for s in data.get("series_accounts", []) if s.get("series_id") == series_id), None)

def _latest_series_for_investor(data: dict, investor_id: str):
    return next((s for s in data.get("series_accounts", []) if s.get("investor_id") == investor_id), None)

@router.get("/api/equalization")
def equalization():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/equalization/share-class")
def create_share_class(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    item = {
        "share_class_id": f"class_{int(time.time())}",
        "class_name": str(payload.get("class_name") or "Class A"),
        "base_nav_per_share": round(float(payload.get("base_nav_per_share") or 100.0), 6),
        "fee_rate_pct": round(float(payload.get("fee_rate_pct") or 0.0), 6),
        "currency": str(payload.get("currency") or "USD"),
        "status": "active",
        "created_at": int(time.time())
    }
    data.setdefault("share_classes", []).insert(0, item)
    data["share_classes"] = data.get("share_classes", [])[:200]
    _save(email, data)
    return {"status": "created", "share_class": item}

@router.post("/api/equalization/series")
def create_series_account(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    investor_id = str(payload.get("investor_id") or "")
    share_class_id = str(payload.get("share_class_id") or "")
    share_class = _find_class(data, share_class_id)
    if not share_class:
        return {"status": "share_class_not_found"}

    commitment = round(float(payload.get("capital_amount") or 0.0), 2)
    nav_ps = round(float(payload.get("nav_per_share") or share_class.get("base_nav_per_share") or 100.0), 6)
    units = round(commitment / nav_ps, 8) if nav_ps > 0 else 0.0

    item = {
        "series_id": f"series_{int(time.time())}",
        "investor_id": investor_id,
        "share_class_id": share_class_id,
        "series_name": str(payload.get("series_name") or f"Series {int(time.time())}"),
        "capital_amount": commitment,
        "nav_per_share": nav_ps,
        "units": units,
        "equalization_credit": 0.0,
        "status": "active",
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }
    data.setdefault("series_accounts", []).insert(0, item)
    data["series_accounts"] = data.get("series_accounts", [])[:2000]
    _save(email, data)
    return {"status": "created", "series_account": item}

@router.post("/api/equalization/event")
def post_equalization_event(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    series_id = str(payload.get("series_id") or "")
    series = _find_series(data, series_id)
    if not series:
        return {"status": "series_not_found"}

    event_type = str(payload.get("event_type") or "performance_allocation")
    rate_pct = round(float(payload.get("rate_pct") or 0.0), 6)
    basis_amount = round(float(payload.get("basis_amount") or series.get("capital_amount") or 0.0), 2)
    amount = round(basis_amount * rate_pct / 100.0, 2)
    if event_type in {"credit", "subscription_adjustment"}:
        series["equalization_credit"] = round(float(series.get("equalization_credit") or 0.0) + amount, 2)
    else:
        series["equalization_credit"] = round(float(series.get("equalization_credit") or 0.0) - amount, 2)
    series["updated_at"] = int(time.time())

    event = {
        "event_id": f"eqevt_{int(time.time())}",
        "series_id": series_id,
        "investor_id": series.get("investor_id"),
        "share_class_id": series.get("share_class_id"),
        "event_type": event_type,
        "basis_amount": basis_amount,
        "rate_pct": rate_pct,
        "amount": amount,
        "post_credit_balance": round(float(series.get("equalization_credit") or 0.0), 2),
        "created_at": int(time.time())
    }
    data.setdefault("equalization_events", []).insert(0, event)
    data["equalization_events"] = data.get("equalization_events", [])[:5000]
    _save(email, data)
    return {"status": "posted", "event": event, "series_account": series}

@router.post("/api/equalization/revalue")
def revalue_series(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    share_class_id = str(payload.get("share_class_id") or "")
    new_nav_per_share = round(float(payload.get("new_nav_per_share") or 0.0), 6)
    if new_nav_per_share <= 0:
        return {"status": "invalid_nav"}
    updated = 0
    for series in data.get("series_accounts", []):
        if series.get("share_class_id") == share_class_id and series.get("status") == "active":
            series["nav_per_share"] = new_nav_per_share
            series["capital_amount"] = round(float(series.get("units") or 0.0) * new_nav_per_share, 2)
            series["updated_at"] = int(time.time())
            updated += 1
    _save(email, data)
    return {"status": "revalued", "updated_series_count": updated, "share_class_id": share_class_id, "new_nav_per_share": new_nav_per_share}

@router.get("/api/equalization/summary")
def equalization_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    share_classes = data.get("share_classes", [])
    series_accounts = data.get("series_accounts", [])
    events = data.get("equalization_events", [])

    total_series_capital = round(sum(float(s.get("capital_amount") or 0.0) for s in series_accounts), 2)
    total_units = round(sum(float(s.get("units") or 0.0) for s in series_accounts), 8)
    total_credit = round(sum(float(s.get("equalization_credit") or 0.0) for s in series_accounts), 2)

    latest_class = share_classes[0] if share_classes else None
    latest_series = series_accounts[0] if series_accounts else None
    latest_event = events[0] if events else None

    return {
        "email": email,
        "share_class_count": len(share_classes),
        "series_account_count": len(series_accounts),
        "event_count": len(events),
        "total_series_capital": total_series_capital,
        "total_units": total_units,
        "total_equalization_credit": total_credit,
        "latest_share_class": latest_class,
        "latest_series_account": latest_series,
        "latest_event": latest_event,
        "share_classes": share_classes[:100],
        "series_accounts": series_accounts[:100],
        "equalization_events": events[:100]
    }
