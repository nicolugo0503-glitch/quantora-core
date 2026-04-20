from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-reconciliation"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
REC_DIR = ARTIFACTS_DIR / "investor_reconciliation"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _nav():
    from backend.app import qnt30597_nav_strike_router as nav
    return nav

def _activity():
    from backend.app import qnt30595_capital_activity_router as activity
    return activity

def _eq():
    from backend.app import qnt30593_equalization_router as eq
    return eq

def _rf():
    from backend.app import qnt30594_rollforward_router as rf
    return rf

def _conf():
    from backend.app import qnt30598_allocation_confirmation_router as conf
    return conf

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    REC_DIR.mkdir(parents=True, exist_ok=True)
    return REC_DIR / f"{_safe(email)}.json"

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

def _latest_or_none(items_key: str, payload: dict):
    items = payload.get(items_key) or []
    return items[0] if items else None

def _run_checks(email: str) -> dict:
    nav_data = _nav()._load(email)
    latest_val = _latest_or_none("valuations", nav_data) or {}

    act_data = _activity()._load(email)
    requests = act_data.get("requests") or []
    processed_subs = round(sum(float(r.get("amount", 0.0)) for r in requests if r.get("status") == "processed" and r.get("activity_type") == "subscription"), 2)
    processed_reds = round(sum(float(r.get("amount", 0.0)) for r in requests if r.get("status") == "processed" and r.get("activity_type") == "redemption"), 2)
    net_flows = round(processed_subs - processed_reds, 2)

    eq_data = _eq()._load(email)
    eq_data = _eq()._recompute_series(eq_data, email)
    series = eq_data.get("series") or []
    total_series_nav = round(sum(float(s.get("series_nav", 0.0)) for s in series), 2)
    total_units = round(sum(float(s.get("units", 0.0)) for s in series), 6)
    nav_per_unit = round(float(series[0].get("nav_per_unit", 0.0)), 6) if series else 0.0
    expected_from_units = round(total_units * nav_per_unit, 2)

    rf_data = _rf()._load(email)
    latest_rf = _latest_or_none("periods", rf_data) or {}
    rf_open = round(float(latest_rf.get("opening_capital", 0.0)), 2)
    rf_end = round(float(latest_rf.get("ending_nav", 0.0)), 2)
    rf_change = round(float(latest_rf.get("net_rollforward_change", 0.0)), 2)

    conf_data = _conf()._load(email)
    notes = conf_data.get("notes") or []
    latest_note = notes[0] if notes else {}
    confirmation_count = len(notes)

    official_nav = round(float(latest_val.get("official_nav", 0.0)), 2)
    allocated_nav = round(float(latest_note.get("allocated_nav", 0.0)), 2)
    note_net_activity = round(float(latest_note.get("net_capital_activity", 0.0)), 2)

    issues = []

    nav_vs_allocations_diff = round(official_nav - allocated_nav, 2)
    nav_vs_allocations_ok = abs(nav_vs_allocations_diff) < 0.01
    if not nav_vs_allocations_ok:
        issues.append({
            "code": "nav_vs_allocations_mismatch",
            "severity": "high",
            "message": f"Official NAV {official_nav} does not match allocated NAV {allocated_nav}.",
            "difference": nav_vs_allocations_diff,
        })

    capital_flow_diff = round(net_flows - note_net_activity, 2)
    capital_flow_ok = abs(capital_flow_diff) < 0.01
    if not capital_flow_ok:
        issues.append({
            "code": "capital_flow_mismatch",
            "severity": "high",
            "message": f"Processed net capital flow {net_flows} does not match confirmation flow {note_net_activity}.",
            "difference": capital_flow_diff,
        })

    equalization_diff = round(total_series_nav - expected_from_units, 2)
    equalization_ok = abs(equalization_diff) < 0.01
    if not equalization_ok:
        issues.append({
            "code": "equalization_drift",
            "severity": "medium",
            "message": f"Series NAV {total_series_nav} does not match units x NAV-per-unit {expected_from_units}.",
            "difference": equalization_diff,
        })

    rollforward_expected_end = round(rf_open + rf_change, 2)
    rollforward_diff = round(rf_end - rollforward_expected_end, 2)
    rollforward_ok = abs(rollforward_diff) < 0.01
    if not rollforward_ok:
        issues.append({
            "code": "rollforward_inconsistency",
            "severity": "high",
            "message": f"Rollforward ending NAV {rf_end} does not equal opening {rf_open} plus change {rf_change}.",
            "difference": rollforward_diff,
        })

    processed_count = sum(1 for r in requests if r.get("status") == "processed")
    confirmations_ok = confirmation_count >= processed_count
    if not confirmations_ok:
        issues.append({
            "code": "missing_confirmations",
            "severity": "medium",
            "message": f"Processed capital activity count {processed_count} exceeds confirmations {confirmation_count}.",
            "difference": processed_count - confirmation_count,
        })

    checks = {
        "nav_vs_allocations": {
            "ok": nav_vs_allocations_ok,
            "official_nav": official_nav,
            "allocated_nav": allocated_nav,
            "difference": nav_vs_allocations_diff,
        },
        "capital_flow": {
            "ok": capital_flow_ok,
            "processed_net_flow": net_flows,
            "confirmation_net_flow": note_net_activity,
            "difference": capital_flow_diff,
        },
        "equalization": {
            "ok": equalization_ok,
            "total_series_nav": total_series_nav,
            "expected_from_units": expected_from_units,
            "difference": equalization_diff,
        },
        "rollforward": {
            "ok": rollforward_ok,
            "opening_capital": rf_open,
            "rollforward_change": rf_change,
            "ending_nav": rf_end,
            "expected_ending_nav": rollforward_expected_end,
            "difference": rollforward_diff,
        },
        "confirmations": {
            "ok": confirmations_ok,
            "processed_activity_count": processed_count,
            "confirmation_count": confirmation_count,
            "difference": confirmation_count - processed_count,
        },
    }

    return {
        "run_id": f"rec_{int(time.time())}",
        "timestamp": int(time.time()),
        "status": "clean" if not issues else "issues_detected",
        "issue_count": len(issues),
        "checks": checks,
        "issues": issues,
    }

@router.get("/api/reconciliation")
def reconciliation():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/reconciliation/run")
def reconciliation_run(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    run = _run_checks(email)
    if payload and payload.get("notes"):
        run["notes"] = str(payload.get("notes"))
    data.setdefault("runs", []).insert(0, run)
    data["runs"] = data["runs"][:200]
    _save(email, data)
    return {"status": run["status"], "run": run, "total_runs": len(data["runs"])}

@router.get("/api/reconciliation/summary")
def reconciliation_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("runs"):
        run = _run_checks(email)
        data.setdefault("runs", []).insert(0, run)
        _save(email, data)
    latest = data["runs"][0]
    clean_runs = sum(1 for r in data.get("runs", []) if r.get("status") == "clean")
    issue_runs = sum(1 for r in data.get("runs", []) if r.get("status") == "issues_detected")
    return {
        "email": email,
        "run_count": len(data.get("runs", [])),
        "clean_run_count": clean_runs,
        "issue_run_count": issue_runs,
        "latest_run": latest,
        "runs": data.get("runs", [])[:50],
    }
