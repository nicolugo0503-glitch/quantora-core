from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time

router = APIRouter(tags=["lp-update-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
COMM_DIR = ARTIFACTS_DIR / "investor_communications"
DIST_DIR = ARTIFACTS_DIR / "lp_update_distribution"

def _main():
    from backend.app import main as app_main
    return app_main

def _crm():
    from backend.app import qnt30572_fundraising_crm_router as crm
    return crm

def _rep():
    from backend.app import qnt30564_reporting_router as rep
    return rep

def _recon():
    from backend.app import qnt30563_reconciliation_router as recon
    return recon

def _comm_path() -> Path:
    COMM_DIR.mkdir(parents=True, exist_ok=True)
    return COMM_DIR / "lp_updates.json"

def _dist_path() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    return DIST_DIR / "distribution_log.json"

def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _save(path: Path, data: dict) -> dict:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _require_admin():
    return _main().require_admin()

def _build_recipients():
    crm = _crm()
    data = crm._load()
    recipients = []
    for inv in data.get("investors", []):
        email = (inv.get("email") or "").strip().lower()
        if not email:
            continue
        recipients.append({
            "investor_id": inv.get("investor_id"),
            "name": inv.get("name"),
            "email": email,
            "stage": inv.get("stage"),
            "type": inv.get("type"),
            "committed_amount": round(float(inv.get("committed_amount") or 0.0), 2),
        })
    return recipients

def _update_payload(update_id: str | None = None):
    rep = _rep()
    recon = _recon()
    recipients = _build_recipients()
    top = recipients[:10]
    reporting = []
    warnings = []
    for r in top:
        try:
            statements = rep._load_statement_store(r["email"])
            latest = (statements.get("statements") or [None])[0]
        except Exception:
            latest = None
        try:
            rec = recon._build_reconciliation(r["email"])
            if rec.get("warnings"):
                warnings.append({"email": r["email"], "warnings": rec.get("warnings", [])})
        except Exception:
            rec = None
        reporting.append({
            "email": r["email"],
            "latest_statement_period": (latest or {}).get("period"),
            "latest_statement_generated_at": (latest or {}).get("generated_at"),
            "reconciliation_status": (rec or {}).get("status") if rec else None,
        })
    return {
        "update_id": update_id or f"lpupd_{int(time.time())}",
        "generated_at": int(time.time()),
        "subject": "Quantora Investor Update",
        "headline": "Capital, operations, and reporting update",
        "body": "This update summarizes current investor reporting, fundraising progression, and operational status across the Quantora platform.",
        "recipient_count": len(recipients),
        "recipient_preview": recipients[:25],
        "reporting_preview": reporting,
        "warning_preview": warnings[:25],
    }

@router.get("/api/lp-updates")
def lp_updates():
    _require_admin()
    return _load(_comm_path(), {"updates": []})

@router.post("/api/lp-updates/generate")
def lp_updates_generate(payload: dict = Body(None)):
    _require_admin()
    store = _load(_comm_path(), {"updates": []})
    subject = None if not payload else (payload.get("subject") or None)
    body = None if not payload else (payload.get("body") or None)
    update = _update_payload()
    if subject:
        update["subject"] = str(subject)
    if body:
        update["body"] = str(body)
    store.setdefault("updates", []).insert(0, update)
    store["updates"] = store["updates"][:100]
    _save(_comm_path(), store)
    return {"status": "generated", "update": update, "total_updates": len(store["updates"])}

@router.get("/api/lp-updates/latest")
def lp_updates_latest():
    _require_admin()
    store = _load(_comm_path(), {"updates": []})
    if not store.get("updates"):
        update = _update_payload()
        store.setdefault("updates", []).insert(0, update)
        _save(_comm_path(), store)
    return {"update": store["updates"][0], "total_updates": len(store["updates"])}

@router.post("/api/lp-updates/distribute")
def lp_updates_distribute(payload: dict = Body(...)):
    _require_admin()
    update_id = payload.get("update_id")
    store = _load(_comm_path(), {"updates": []})
    update = next((u for u in store.get("updates", []) if u.get("update_id") == update_id), None)
    if not update:
        raise HTTPException(status_code=404, detail="Update not found")
    dist = _load(_dist_path(), {"events": []})
    event = {
        "distribution_id": f"dist_{int(time.time())}",
        "update_id": update_id,
        "distributed_at": int(time.time()),
        "recipient_count": int(update.get("recipient_count") or 0),
        "channel": (payload.get("channel") or "portal_simulated").strip().lower(),
        "status": "sent_simulated",
    }
    dist.setdefault("events", []).insert(0, event)
    dist["events"] = dist["events"][:200]
    _save(_dist_path(), dist)
    update["last_distribution"] = event
    _save(_comm_path(), store)
    return {"status": "distributed", "event": event}

@router.get("/api/lp-updates/distribution-log")
def lp_updates_distribution_log():
    _require_admin()
    return _load(_dist_path(), {"events": []})
