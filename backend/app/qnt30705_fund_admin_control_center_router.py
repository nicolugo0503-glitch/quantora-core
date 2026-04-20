from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["fund-admin-control-center"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ADMIN_DIR = ARTIFACTS_DIR / "fund_admin_control_center"
DEMO_EMAIL = "operator@quantora.test"

DEFAULT_POLICY = {
    "lock_period_after_close": True,
    "require_clean_reconciliation": True,
    "require_safe_delivery_context": True,
    "max_nav_break_tolerance": 0.01,
    "default_hurdle_rate_pct": 8.0,
    "default_gp_carry_pct": 20.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger


def _waterfall():
    from backend.app import qnt30625_waterfall_router as waterfall
    return waterfall


def _statements():
    from backend.app import qnt30627_statement_batch_router as statements
    return statements


def _performance():
    from backend.app import qnt30628_performance_engine_router as perf
    return perf


def _ops():
    from backend.app import qnt30636_operations_fund_admin_router as ops
    return ops


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _operator():
    from backend.app import qnt30702_operator_command_console_router as op
    return op


def _delivery():
    from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
    return delivery


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    return ADMIN_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "close_runs": [],
            "nav_history": [],
            "capital_flows": [],
            "compliance_events": [],
            "statement_events": [],
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


def _append(store: dict, key: str, row: dict, limit: int = 250):
    store.setdefault(key, []).insert(0, row)
    store[key] = store.get(key, [])[:limit]


def _ledger_totals(email: str) -> dict:
    ledger = _ledger()._load(email)
    accounts = ledger.get("accounts") or []
    entries = ledger.get("entries") or []
    allocations = ledger.get("allocations") or []
    committed = round(sum(float(a.get("committed_capital") or 0.0) for a in accounts), 2)
    funded = round(sum(float(a.get("funded_capital") or 0.0) for a in accounts), 2)
    nav = round(sum(float(a.get("nav") or 0.0) for a in accounts), 2)
    unfunded = round(committed - funded, 2)
    latest_account = accounts[0] if accounts else None
    latest_entry = entries[0] if entries else None
    latest_allocation = allocations[0] if allocations else None
    return {
        "investor_count": len(accounts),
        "account_count": len(accounts),
        "entry_count": len(entries),
        "allocation_count": len(allocations),
        "committed_capital": committed,
        "funded_capital": funded,
        "unfunded_capital": unfunded,
        "current_nav": nav,
        "latest_account": latest_account,
        "latest_entry": latest_entry,
        "latest_allocation": latest_allocation,
        "accounts": accounts[:50],
    }


def _reconciliation_status(nav: float, perf_current_nav: float, tolerance: float) -> dict:
    diff = round(float(perf_current_nav or 0.0) - float(nav or 0.0), 2)
    pct = 0.0 if abs(nav) < 1e-9 else abs(diff) / max(abs(nav), 1.0)
    status = "clean" if pct <= float(tolerance or 0.01) else "break"
    return {
        "status": status,
        "nav_difference": diff,
        "difference_pct": round(pct, 6),
        "tolerance": float(tolerance or 0.01),
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ledger = _ledger_totals(email)
    perf = _performance()._live_summary(email)
    perf_summary = perf.get("summary") or {}
    waterfall_store = _waterfall()._load(email)
    waterfall_runs = waterfall_store.get("runs") or []
    notices = waterfall_store.get("distribution_notices") or []
    statements = _statements()._load(email)
    periods = list((statements.get("periods") or {}).values())
    period_rows = sorted(periods, key=lambda x: x.get("period") or "", reverse=True)
    ops = _ops()._ops_summary(email)
    safety = _safety()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    operator = _operator()._summary_for_email(email)
    delivery = _delivery()._summary_for_email(email)
    recon = _reconciliation_status(ledger.get("current_nav"), perf_summary.get("current_nav") or ledger.get("current_nav"), policy.get("max_nav_break_tolerance"))
    close_runs = store.get("close_runs") or []
    latest_close = close_runs[0] if close_runs else None
    readiness = "ready"
    blockers = []
    if policy.get("require_clean_reconciliation") and recon.get("status") != "clean":
        readiness = "attention"
        blockers.append("nav reconciliation break")
    if ((safety.get("safety_layer_status") or {}).get("posture") or "UNKNOWN").upper() == "BLOCKED":
        readiness = "blocked"
        blockers.append("live broker safety posture blocked")
    if bool((safety.get("safety_layer_status") or {}).get("kill_switch")):
        readiness = "blocked"
        blockers.append("kill switch active")
    if policy.get("require_safe_delivery_context") and int(delivery.get("pending_ack_count") or 0) > 10:
        readiness = "attention"
        blockers.append("delivery acknowledgement backlog above threshold")
    if int(ops.get("open_exception_count") or 0) > 0 or int(ops.get("open_break_count") or 0) > 0:
        if readiness != "blocked":
            readiness = "attention"
        blockers.append("operations exceptions require resolution")
    return {
        "mission": "QNT30705",
        "generated_at": _now_iso(),
        "period": _current_period(),
        "policy": policy,
        "fund_admin_status": {
            "readiness": readiness,
            "blockers": blockers,
            "period_locked": bool((ops.get("period_lock") or {}).get("locked")),
            "latest_close_status": (latest_close or {}).get("status"),
        },
        "aum": ledger.get("current_nav"),
        "capital_summary": ledger,
        "performance_summary": perf_summary,
        "reconciliation": recon,
        "waterfall_summary": {
            "run_count": len(waterfall_runs),
            "notice_count": len(notices),
            "published_notice_count": len([n for n in notices if n.get("status") == "published"]),
            "latest_run": waterfall_runs[0] if waterfall_runs else None,
        },
        "statement_summary": {
            "period_count": len(period_rows),
            "locked_period_count": len([p for p in period_rows if p.get("status") == "locked"]),
            "latest_period": period_rows[0] if period_rows else None,
        },
        "ops_summary": {
            "nav_status": ops.get("nav_status"),
            "reconciliation_status": ops.get("reconciliation_status"),
            "open_break_count": ops.get("open_break_count"),
            "open_exception_count": ops.get("open_exception_count"),
            "close_packet_count": ops.get("close_packet_count"),
        },
        "institutional_context": {
            "safety_posture": (safety.get("safety_layer_status") or {}).get("posture") or "UNKNOWN",
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
            "active_release_version": release.get("active_version"),
            "operator_mode": operator.get("active_mode"),
            "pending_delivery_ack_count": delivery.get("pending_ack_count"),
        },
        "close_runs": close_runs[:20],
        "capital_flows": (store.get("capital_flows") or [])[:30],
        "compliance_events": (store.get("compliance_events") or [])[:30],
        "statement_events": (store.get("statement_events") or [])[:30],
    }


def _seed_demo_foundation(email: str):
    ledger_mod = _ledger()
    ledger = ledger_mod._load(email)
    if not (ledger.get("accounts") or []):
        now = _now_ts()
        accounts = [
            {
                "account_id": f"acct_{now}_1",
                "investor_id": "INV-001",
                "investor_name": "Northstar Family Office",
                "status": "open",
                "committed_capital": 600000.0,
                "funded_capital": 500000.0,
                "unfunded_capital": 100000.0,
                "nav": 540000.0,
                "ownership_pct": 60.0,
                "created_at": now,
                "updated_at": now,
            },
            {
                "account_id": f"acct_{now}_2",
                "investor_id": "INV-002",
                "investor_name": "Orion Capital Partners",
                "status": "open",
                "committed_capital": 400000.0,
                "funded_capital": 350000.0,
                "unfunded_capital": 50000.0,
                "nav": 360000.0,
                "ownership_pct": 40.0,
                "created_at": now,
                "updated_at": now,
            },
        ]
        entries = [
            {"entry_id": f"entry_{now}_1", "investor_id": "INV-001", "account_id": accounts[0]["account_id"], "entry_type": "funding", "amount": 500000.0, "description": "initial funding", "created_at": now},
            {"entry_id": f"entry_{now}_2", "investor_id": "INV-002", "account_id": accounts[1]["account_id"], "entry_type": "funding", "amount": 350000.0, "description": "initial funding", "created_at": now},
            {"entry_id": f"entry_{now}_3", "investor_id": "INV-001", "account_id": accounts[0]["account_id"], "entry_type": "gain", "amount": 40000.0, "description": "realized pnl", "created_at": now},
            {"entry_id": f"entry_{now}_4", "investor_id": "INV-002", "account_id": accounts[1]["account_id"], "entry_type": "gain", "amount": 10000.0, "description": "realized pnl", "created_at": now},
        ]
        allocations = [
            {"allocation_id": f"alloc_{now}_1", "investor_id": "INV-001", "strategy": "institutional_core", "sleeve": "global-macro", "amount": 300000.0, "status": "active", "created_at": now},
            {"allocation_id": f"alloc_{now}_2", "investor_id": "INV-002", "strategy": "institutional_core", "sleeve": "equity-long-short", "amount": 250000.0, "status": "active", "created_at": now},
        ]
        ledger["accounts"] = accounts
        ledger["entries"] = entries
        ledger["allocations"] = allocations
        ledger_mod._save(email, ledger)

    waterfall_mod = _waterfall()
    waterfall = waterfall_mod._load(email)
    if not (waterfall.get("runs") or []):
        run, notices = waterfall_mod._build_run(email, distributable_profit=50000.0, hurdle_rate=DEFAULT_POLICY["default_hurdle_rate_pct"], gp_carry_pct=DEFAULT_POLICY["default_gp_carry_pct"])
        waterfall.setdefault("runs", []).insert(0, run)
        waterfall["distribution_notices"] = notices
        waterfall_mod._save(email, waterfall)

    statements_mod = _statements()
    periods = (statements_mod._load(email).get("periods") or {})
    if not periods:
        try:
            statements_mod.investor_statements_bootstrap({})
        except Exception:
            pass

    try:
        _ops().operations_fund_admin_bootstrap({"notes": "QNT30705 bootstrap"})
    except Exception:
        try:
            _ops()._create_close_packet(email, "QNT30705 bootstrap")
        except Exception:
            pass

    try:
        _safety().live_broker_safety_layer_bootstrap_demo({"email": email})
    except Exception:
        pass

    try:
        _delivery().investor_delivery_pack_system_bootstrap_demo({"email": email})
    except Exception:
        pass


def _run_close_for_email(email: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    summary_before = _summary_for_email(email)
    recon = summary_before.get("reconciliation") or {}
    if policy.get("require_clean_reconciliation") and recon.get("status") != "clean":
        raise HTTPException(status_code=409, detail="cannot close period while reconciliation status is not clean")

    delivery = _delivery()._summary_for_email(email)
    if policy.get("require_safe_delivery_context") and int(delivery.get("pending_ack_count") or 0) > 10:
        raise HTTPException(status_code=409, detail="cannot close period while delivery acknowledgements are backlogged")

    waterfall_mod = _waterfall()
    waterfall_store = waterfall_mod._load(email)
    if not (waterfall_store.get("runs") or []):
        run, notices = waterfall_mod._build_run(email, distributable_profit=float(payload.get("distributable_profit") or 50000.0), hurdle_rate=float(policy.get("default_hurdle_rate_pct") or 8.0), gp_carry_pct=float(policy.get("default_gp_carry_pct") or 20.0))
        waterfall_store.setdefault("runs", []).insert(0, run)
        waterfall_store["distribution_notices"] = notices + (waterfall_store.get("distribution_notices") or [])
        waterfall_mod._save(email, waterfall_store)

    close_run = {
        "close_id": f"facc_{time.time_ns()}",
        "mission": "QNT30705",
        "period": _current_period(),
        "created_at": _now_iso(),
        "aum": summary_before.get("aum"),
        "reconciliation_status": recon.get("status"),
        "nav_difference": recon.get("nav_difference"),
        "statement_period_count": int(summary_before.get("statement_summary", {}).get("period_count") or 0),
        "waterfall_run_count": int(summary_before.get("waterfall_summary", {}).get("run_count") or 0),
        "delivery_pack_count": int(delivery.get("pack_count") or 0),
        "notes": payload.get("notes") or "fund administration close run",
        "status": "closed",
    }
    _append(store, "close_runs", close_run, limit=120)
    _append(store, "nav_history", {"period": _current_period(), "current_nav": summary_before.get("aum"), "recorded_at": _now_iso(), "source": "fund_admin_close"}, limit=240)
    _append(store, "compliance_events", {"event_id": f"cmp_{time.time_ns()}", "type": "period_close", "period": _current_period(), "recorded_at": _now_iso(), "notes": close_run["notes"]}, limit=300)
    _append(store, "statement_events", {"event_id": f"stmt_{time.time_ns()}", "type": "statement_linkage", "period": _current_period(), "recorded_at": _now_iso(), "statement_periods": summary_before.get("statement_summary", {}).get("period_count")}, limit=300)
    _save(email, store)

    if bool(policy.get("lock_period_after_close")):
        try:
            _ops().operations_fund_admin_lock_period({"reason": "QNT30705 close complete"})
        except Exception:
            pass

    return {"status": "closed", "close_run": close_run, "summary": _summary_for_email(email)}


@router.get("/api/fund-admin-control-center/summary")
def fund_admin_control_center_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/fund-admin-control-center/bootstrap-demo")
def fund_admin_control_center_bootstrap_demo(payload: dict = Body(default=None)):
    session_email = None
    try:
        session_email = _require_user().get("email")
    except HTTPException:
        pass
    email = (payload or {}).get("email") or session_email or DEMO_EMAIL
    _seed_demo_foundation(email)
    store = _load(email)
    _append(store, "capital_flows", {"flow_id": f"flow_{time.time_ns()}", "type": "subscription", "amount": 850000.0, "recorded_at": _now_iso(), "notes": "bootstrap seeded capital base"}, limit=300)
    _save(email, store)
    return {"status": "bootstrapped", "summary": _summary_for_email(email)}


@router.post("/api/fund-admin-control-center/run-close")
def fund_admin_control_center_run_close(payload: dict = Body(default=None)):
    session = _require_user()
    return _run_close_for_email(session.get("email"), payload)


@router.post("/api/fund-admin-control-center/record-flow")
def fund_admin_control_center_record_flow(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    flow_type = (payload.get("type") or "capital_activity").strip().lower()
    amount = round(float(payload.get("amount") or 0.0), 2)
    if abs(amount) < 1e-9:
        raise HTTPException(status_code=400, detail="amount required")
    store = _load(email)
    row = {
        "flow_id": f"flow_{time.time_ns()}",
        "type": flow_type,
        "amount": amount,
        "investor_id": payload.get("investor_id"),
        "recorded_at": _now_iso(),
        "notes": payload.get("notes") or "",
    }
    _append(store, "capital_flows", row, limit=300)
    if flow_type in {"distribution", "fee", "capital_call", "subscription", "redemption"}:
        _append(store, "compliance_events", {"event_id": f"cmp_{time.time_ns()}", "type": flow_type, "period": _current_period(), "recorded_at": _now_iso(), "notes": row["notes"], "amount": amount}, limit=300)
    _save(email, store)
    return {"status": "recorded", "flow": row, "summary": _summary_for_email(email)}


@router.post("/api/fund-admin-control-center/policy")
def fund_admin_control_center_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    for key, value in payload.items():
        if key in DEFAULT_POLICY:
            policy[key] = value
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy, "summary": _summary_for_email(email)}
