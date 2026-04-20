from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["autonomous-break-resolution-suggestions"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
SUG_DIR = ARTIFACTS_DIR / "autonomous_break_resolution_suggestions"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _alerts():
    from backend.app import qnt30606_break_alert_router as alerts
    return alerts

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    SUG_DIR.mkdir(parents=True, exist_ok=True)
    return SUG_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "runs": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _suggest_for_alert(alert: dict) -> dict:
    code = str(alert.get("code") or "")
    severity = str(alert.get("severity") or "medium")
    source = str(alert.get("source") or "")
    message = str(alert.get("message") or "")

    playbook = {
        "cash_mismatch": {
            "suggestion": "Re-import broker cash, rerun three-way reconciliation, and verify recent capital activity processing.",
            "recommended_action": "rerun_threeway_after_cash_sync",
            "confidence": 0.91,
        },
        "position_mismatch": {
            "suggestion": "Re-sync live broker positions, compare symbol-level quantities, and inspect missing or duplicated trade attribution.",
            "recommended_action": "rerun_position_sync_and_broker_match",
            "confidence": 0.92,
        },
        "nav_consistency_break": {
            "suggestion": "Recompute official NAV after rollforward and equalization refresh, then rerun three-way reconciliation.",
            "recommended_action": "refresh_nav_and_rerun_threeway",
            "confidence": 0.89,
        },
        "missing_in_broker": {
            "suggestion": "Check whether trades failed at broker, were delayed, or were not imported; rerun broker reconciliation after sync.",
            "recommended_action": "rerun_broker_sync_and_match",
            "confidence": 0.90,
        },
        "unexpected_broker_trade": {
            "suggestion": "Investigate manual or external broker executions not represented internally, then map or quarantine them.",
            "recommended_action": "quarantine_unexpected_broker_trade",
            "confidence": 0.88,
        },
        "nav_vs_allocations_mismatch": {
            "suggestion": "Rebuild allocation confirmations from the latest official valuation and verify contract note generation.",
            "recommended_action": "regenerate_allocation_confirmation",
            "confidence": 0.87,
        },
        "capital_flow_mismatch": {
            "suggestion": "Cross-check processed subscriptions/redemptions against confirmations and dealing-day cutoff status.",
            "recommended_action": "reconcile_capital_flow_and_confirmations",
            "confidence": 0.90,
        },
        "equalization_drift": {
            "suggestion": "Refresh series accounting, verify units and NAV-per-unit, then rerun equalization and rollforward.",
            "recommended_action": "refresh_equalization_series",
            "confidence": 0.89,
        },
        "rollforward_inconsistency": {
            "suggestion": "Recompute rollforward from opening capital, flows, and ending NAV before re-striking valuation.",
            "recommended_action": "rebuild_rollforward",
            "confidence": 0.91,
        },
        "missing_confirmations": {
            "suggestion": "Generate missing allocation confirmations for processed capital activity and capture acknowledgements.",
            "recommended_action": "generate_missing_confirmations",
            "confidence": 0.86,
        },
    }

    base = playbook.get(code, {
        "suggestion": "Review the underlying ledger state and rerun the relevant reconciliation workflow.",
        "recommended_action": "manual_investigation",
        "confidence": 0.65,
    })

    return {
        "alert_id": alert.get("alert_id"),
        "source": source,
        "code": code,
        "severity": severity,
        "message": message,
        "suggestion": base["suggestion"],
        "recommended_action": base["recommended_action"],
        "confidence": base["confidence"],
        "generated_at": int(time.time()),
        "status": "proposed",
    }

@router.get("/api/resolution-suggestions")
def resolution_suggestions():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/resolution-suggestions/run")
def resolution_suggestions_run(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)

    alerts_data = _alerts()._load(email)
    open_alerts = [a for a in alerts_data.get("alerts", []) if a.get("status") in {"open", "acknowledged"}]
    suggestions = [_suggest_for_alert(a) for a in open_alerts]

    run = {
        "run_id": f"suggest_{int(time.time())}",
        "timestamp": int(time.time()),
        "open_alert_count": len(open_alerts),
        "suggestion_count": len(suggestions),
        "status": "suggestions_generated" if suggestions else "no_open_alerts",
        "suggestions": suggestions[:200],
    }
    if payload and payload.get("notes"):
        run["notes"] = str(payload.get("notes"))
    data.setdefault("runs", []).insert(0, run)
    data["runs"] = data["runs"][:200]
    _save(email, data)
    return {"status": run["status"], "run": run, "total_runs": len(data["runs"])}

@router.post("/api/resolution-suggestions/accept")
def resolution_suggestions_accept(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    alert_id = str(payload.get("alert_id") or "")
    data = _load(email)
    if not data.get("runs"):
        return {"status": "no_runs"}
    latest = data["runs"][0]
    suggestion = next((s for s in latest.get("suggestions", []) if s.get("alert_id") == alert_id), None)
    if not suggestion:
        return {"status": "not_found"}
    suggestion["status"] = "accepted"
    suggestion["accepted_at"] = int(time.time())
    _save(email, data)
    return {"status": "accepted", "suggestion": suggestion}

@router.get("/api/resolution-suggestions/summary")
def resolution_suggestions_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("runs"):
        alerts_data = _alerts()._load(email)
        open_alerts = [a for a in alerts_data.get("alerts", []) if a.get("status") in {"open", "acknowledged"}]
        suggestions = [_suggest_for_alert(a) for a in open_alerts]
        run = {
            "run_id": f"suggest_{int(time.time())}",
            "timestamp": int(time.time()),
            "open_alert_count": len(open_alerts),
            "suggestion_count": len(suggestions),
            "status": "suggestions_generated" if suggestions else "no_open_alerts",
            "suggestions": suggestions[:200],
        }
        data.setdefault("runs", []).insert(0, run)
        _save(email, data)
    latest = data["runs"][0]
    accepted = sum(
        1
        for run in data.get("runs", [])
        for s in run.get("suggestions", [])
        if s.get("status") == "accepted"
    )
    return {
        "email": email,
        "run_count": len(data.get("runs", [])),
        "latest_run": latest,
        "latest_suggestion_count": latest.get("suggestion_count", 0),
        "accepted_suggestion_count": accepted,
        "runs": data.get("runs", [])[:50],
    }
