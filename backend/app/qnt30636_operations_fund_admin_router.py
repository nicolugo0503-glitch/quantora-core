from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["operations-fund-administration-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
OPS_DIR = ARTIFACTS_DIR / "operations_fund_admin_layer"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _fund_close():
    from backend.app import qnt30581_fund_close_router as fund_close
    return fund_close


def _recon():
    from backend.app import qnt30600_reconciliation_router as recon
    return recon


def _exc():
    from backend.app import qnt30601_exception_resolution_router as exc
    return exc


def _audit():
    from backend.app import qnt30602_audit_trail_router as audit
    return audit


def _breaks():
    from backend.app import qnt30606_break_alert_router as breaks
    return breaks


def _correction():
    from backend.app import qnt30608_correction_execution_router as correction
    return correction


def _supervisory():
    from backend.app import qnt30609_supervisory_control_router as supervisory
    return supervisory


def _statements():
    from backend.app import qnt30627_statement_batch_router as statements
    return statements


def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger


def _performance():
    from backend.app import qnt30628_performance_engine_router as performance
    return performance


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    return OPS_DIR / f"{_safe(email)}.json"


def _now_ts() -> int:
    return int(time.time())


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _require_user():
    return _mu()._require_session()


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "close_packets": [],
            "period_lock": {},
            "ops_notes": [],
            "created_at": _now_ts(),
            "updated_at": _now_ts(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict) -> dict:
    data["updated_at"] = _now_ts()
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _latest(items: list[dict]) -> dict:
    return items[0] if items else {}


def _ops_summary(email: str) -> dict:
    store = _load(email)
    ledger = _ledger()._load(email)
    fund_close = _fund_close().fund_close_summary()
    recon = _recon().reconciliation_summary()
    exc = _exc().reconciliation_exceptions_summary()
    audit = _audit().audit_summary()
    break_summary = _breaks().break_alerts_summary()
    correction_summary = _correction().correction_execution_summary()
    supervisory_summary = _supervisory().supervisory_control_summary()
    statements = _statements().investor_statements_summary(_period())
    perf = _performance().performance_engine_summary()

    latest_packet = _latest(store.get("close_packets", []))
    latest_recon = recon.get("latest_run") or {}
    latest_break = break_summary.get("latest_alert") or {}

    return {
        "email": email,
        "period": _period(),
        "nav_status": "locked" if store.get("period_lock", {}).get("locked") else "open",
        "reconciliation_status": recon.get("status", "unknown"),
        "open_break_count": int(break_summary.get("open_alert_count") or 0),
        "open_exception_count": int(exc.get("open_count") or 0),
        "close_packet_count": len(store.get("close_packets", [])),
        "statement_batch_count": int(statements.get("statement_count") or 0),
        "capital_summary": {
            "committed": round(float(ledger.get("totals", {}).get("committed_capital", 0.0)), 2),
            "funded": round(float(ledger.get("totals", {}).get("funded_capital", 0.0)), 2),
            "nav": round(float(ledger.get("totals", {}).get("current_nav", 0.0)), 2),
            "investor_count": int(ledger.get("summary", {}).get("investor_count", 0)),
        },
        "performance_summary": perf,
        "fund_close_summary": fund_close,
        "reconciliation_summary": recon,
        "exception_summary": exc,
        "audit_summary": audit,
        "break_summary": break_summary,
        "correction_summary": correction_summary,
        "supervisory_summary": supervisory_summary,
        "latest_close_packet": latest_packet,
        "latest_reconciliation_run": latest_recon,
        "latest_break_alert": latest_break,
        "period_lock": store.get("period_lock", {}),
        "close_packets": store.get("close_packets", [])[:24],
        "ops_notes": store.get("ops_notes", [])[:50],
    }


def _create_close_packet(email: str, notes: str = "") -> dict:
    store = _load(email)
    summary = _ops_summary(email)
    packet = {
        "packet_id": f"ops_{time.time_ns()}",
        "period": _period(),
        "created_at": _now_ts(),
        "status": "ready" if summary.get("reconciliation_status") == "clean" and summary.get("open_break_count") == 0 else "requires_attention",
        "nav_status": summary.get("nav_status"),
        "reconciliation_status": summary.get("reconciliation_status"),
        "open_break_count": summary.get("open_break_count"),
        "open_exception_count": summary.get("open_exception_count"),
        "statement_batch_count": summary.get("statement_batch_count"),
        "capital_summary": summary.get("capital_summary"),
        "performance_return_pct": summary.get("performance_summary", {}).get("portfolio_return_pct"),
        "notes": notes.strip(),
    }
    store.setdefault("close_packets", []).insert(0, packet)
    store["close_packets"] = store.get("close_packets", [])[:120]
    _save(email, store)
    return packet


@router.get("/api/operations-fund-admin/summary")
def operations_fund_admin_summary():
    session = _require_user()
    return _ops_summary(session.get("email"))


@router.post("/api/operations-fund-admin/bootstrap-demo")
def operations_fund_admin_bootstrap(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    notes = str((payload or {}).get("notes") or "")

    # Seed a statement batch for the current period if needed.
    statement_summary = _statements().investor_statements_summary(_period())
    if int(statement_summary.get("statement_count") or 0) == 0:
        try:
            _statements().investor_statements_bootstrap({})
        except Exception:
            pass

    # Run a reconciliation pass and import current exceptions.
    try:
        _recon().reconciliation_run({"notes": "QNT30636 operational bootstrap"})
    except Exception:
        pass
    try:
        _exc().reconciliation_exceptions_import_latest({})
    except Exception:
        pass

    packet = _create_close_packet(email, notes or "QNT30636 bootstrap packet")
    summary = _ops_summary(email)
    return {"status": "bootstrapped", "packet": packet, "summary": summary}


@router.post("/api/operations-fund-admin/run-close")
def operations_fund_admin_run_close(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    notes = str((payload or {}).get("notes") or "")
    packet = _create_close_packet(email, notes)
    return {"status": packet.get("status"), "packet": packet, "summary": _ops_summary(email)}


@router.post("/api/operations-fund-admin/lock-period")
def operations_fund_admin_lock_period(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    reason = str((payload or {}).get("reason") or "period closed via QNT30636").strip()
    lock = {
        "period": _period(),
        "locked": True,
        "locked_at": _now_ts(),
        "reason": reason,
    }
    store["period_lock"] = lock
    store.setdefault("ops_notes", []).insert(0, {"type": "period_lock", "timestamp": _now_ts(), "reason": reason})
    store["ops_notes"] = store.get("ops_notes", [])[:200]
    _save(email, store)
    return {"status": "locked", "period_lock": lock, "summary": _ops_summary(email)}


@router.post("/api/operations-fund-admin/unlock-period")
def operations_fund_admin_unlock_period(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    reason = str((payload or {}).get("reason") or "manual reopen").strip()
    lock = {
        "period": _period(),
        "locked": False,
        "locked_at": None,
        "reason": reason,
        "updated_at": _now_ts(),
    }
    store["period_lock"] = lock
    store.setdefault("ops_notes", []).insert(0, {"type": "period_unlock", "timestamp": _now_ts(), "reason": reason})
    store["ops_notes"] = store.get("ops_notes", [])[:200]
    _save(email, store)
    return {"status": "unlocked", "period_lock": lock, "summary": _ops_summary(email)}
