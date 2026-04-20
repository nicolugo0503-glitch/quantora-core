from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-waterfall-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
WATERFALL_DIR = ARTIFACTS_DIR / "investor_waterfall_engine"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email: str) -> Path:
    WATERFALL_DIR.mkdir(parents=True, exist_ok=True)
    return WATERFALL_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "runs": [],
            "distribution_notices": [],
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

def _build_run(email: str, distributable_profit: float, hurdle_rate: float, gp_carry_pct: float):
    ledger_data = _ledger()._load(email)
    accounts = ledger_data.get("accounts", []) or []
    total_nav = round(sum(float(a.get("nav") or 0.0) for a in accounts), 2)
    total_funded = round(sum(float(a.get("funded_capital") or 0.0) for a in accounts), 2)
    distributable_profit = round(float(distributable_profit or 0.0), 2)
    hurdle_rate = float(hurdle_rate or 0.0)
    gp_carry_pct = float(gp_carry_pct or 0.0)

    hurdle_amount = round(total_funded * hurdle_rate / 100.0, 2)
    above_hurdle = max(0.0, round(distributable_profit - hurdle_amount, 2))
    gp_carry = round(above_hurdle * gp_carry_pct / 100.0, 2)
    lp_distribution_pool = round(distributable_profit - gp_carry, 2)

    investor_allocations = []
    notices = []

    for account in accounts:
        ownership_pct = float(account.get("ownership_pct") or 0.0)
        lp_dist = round(lp_distribution_pool * ownership_pct / 100.0, 2)
        allocation = {
            "investor_id": account.get("investor_id"),
            "investor_name": account.get("investor_name"),
            "ownership_pct": round(ownership_pct, 6),
            "funded_capital": round(float(account.get("funded_capital") or 0.0), 2),
            "distribution_amount": lp_dist,
            "account_id": account.get("account_id")
        }
        investor_allocations.append(allocation)
        notices.append({
            "notice_id": f"notice_{int(time.time())}_{account.get('investor_id')}",
            "investor_id": account.get("investor_id"),
            "investor_name": account.get("investor_name"),
            "distribution_amount": lp_dist,
            "status": "draft",
            "created_at": int(time.time())
        })

    return {
        "run_id": f"waterfall_{int(time.time())}",
        "timestamp": int(time.time()),
        "total_nav": total_nav,
        "total_funded_capital": total_funded,
        "distributable_profit": distributable_profit,
        "hurdle_rate_pct": hurdle_rate,
        "hurdle_amount": hurdle_amount,
        "gp_carry_pct": gp_carry_pct,
        "gp_carry_amount": gp_carry,
        "lp_distribution_pool": lp_distribution_pool,
        "investor_allocations": investor_allocations[:500],
        "notice_count": len(notices),
        "status": "calculated"
    }, notices

@router.get("/api/waterfall")
def waterfall():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/waterfall/run")
def waterfall_run(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    run, notices = _build_run(
        email,
        float(payload.get("distributable_profit") or 0.0),
        float(payload.get("hurdle_rate_pct") or 0.0),
        float(payload.get("gp_carry_pct") or 0.0),
    )
    data.setdefault("runs", []).insert(0, run)
    data["runs"] = data.get("runs", [])[:300]
    data["distribution_notices"] = notices + data.get("distribution_notices", [])
    data["distribution_notices"] = data["distribution_notices"][:2000]
    _save(email, data)
    return {"status": "calculated", "run": run, "notices_created": len(notices)}

@router.post("/api/waterfall/notice/publish")
def publish_notice(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    notice_id = str(payload.get("notice_id") or "")
    data = _load(email)
    item = next((n for n in data.get("distribution_notices", []) if n.get("notice_id") == notice_id), None)
    if not item:
        return {"status": "not_found"}
    item["status"] = "published"
    item["published_at"] = int(time.time())
    _save(email, data)
    return {"status": "published", "notice": item}

@router.get("/api/waterfall/summary")
def waterfall_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    runs = data.get("runs", [])
    notices = data.get("distribution_notices", [])
    published = sum(1 for n in notices if n.get("status") == "published")
    latest_run = runs[0] if runs else None
    latest_notice = notices[0] if notices else None
    return {
        "email": email,
        "run_count": len(runs),
        "notice_count": len(notices),
        "published_notice_count": published,
        "latest_run": latest_run,
        "latest_notice": latest_notice,
        "runs": runs[:100],
        "distribution_notices": notices[:100]
    }
