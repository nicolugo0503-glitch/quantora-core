from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["reporting-disclosure-automation-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "reporting_disclosure_automation_layer"
DEFAULT_POLICY = {
    "retain_runs": 180,
    "min_automation_score": 82.0,
    "max_open_exceptions": 1,
    "max_staleness_hours": 48.0,
    "min_delivery_success_pct": 92.0,
    "min_template_integrity_score": 88.0,
    "min_disclosure_completeness_pct": 90.0,
    "require_transparency_approved": True,
    "require_delivery_ready": True,
    "require_fund_admin_ready": True,
    "require_release_clear": True,
    "require_operator_review_for_exceptions": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _delivery():
    from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
    return delivery


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as admin
    return admin


def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic


def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery


def _transparency():
    from backend.app import qnt30714_investor_transparency_engine_router as transparency
    return transparency


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "runs": [],
            "exceptions": [],
            "automation_book": [],
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


def _append(store: dict, key: str, row: dict, limit: int):
    store.setdefault(key, []).insert(0, row)
    store[key] = store.get(key, [])[:limit]


def _cross_system_context(email: str) -> dict:
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    delivery = _delivery()._summary_for_email(email)
    admin = _fund_admin()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    transparency = _transparency()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": {
            "posture": (operator.get("operator_console_status") or {}).get("posture"),
            "override_required": bool((operator.get("operator_console_status") or {}).get("override_required", False)),
        },
        "release": {
            "posture": (release.get("institutional_release_control_status") or {}).get("posture"),
            "current_version": (release.get("institutional_release_control_status") or {}).get("current_version") or release.get("active_version"),
        },
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
        },
        "delivery": {
            "investor_ready": (delivery.get("delivery_pack_status") or {}).get("investor_ready"),
            "blocked": (delivery.get("delivery_pack_status") or {}).get("blocked"),
            "pending_ack_count": delivery.get("pending_ack_count"),
            "delivered_count": delivery.get("delivered_count"),
        },
        "fund_admin": {
            "readiness": (admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": float(admin.get("aum") or 0.0),
            "reported_nav": float((admin.get("nav") or {}).get("reported_nav") or 0.0),
        },
        "forensic": {
            "posture": (forensic.get("forensic_status") or {}).get("posture"),
            "critical_open_count": (forensic.get("forensic_status") or {}).get("critical_open_count"),
        },
        "recovery": {
            "posture": (recovery.get("recovery_status") or {}).get("posture"),
            "safe_mode": (recovery.get("recovery_status") or {}).get("safe_mode"),
            "valid_state": (recovery.get("current_validation") or {}).get("valid_state"),
        },
        "transparency": {
            "posture": (transparency.get("investor_transparency_status") or {}).get("posture"),
            "latest_score": (transparency.get("investor_transparency_status") or {}).get("latest_score"),
            "packet_count": (transparency.get("investor_transparency_status") or {}).get("packet_count"),
            "exception_count": (transparency.get("investor_transparency_status") or {}).get("exception_count"),
        },
    }


def _score_run(payload: dict, ctx: dict, policy: dict) -> dict:
    template_integrity_score = float(payload.get("template_integrity_score") or 0.0)
    disclosure_completeness_pct = float(payload.get("disclosure_completeness_pct") or 0.0)
    delivery_success_pct = float(payload.get("delivery_success_pct") or 0.0)
    report_staleness_hours = float(payload.get("report_staleness_hours") or 0.0)
    open_exceptions = int(payload.get("open_exceptions") or 0)
    automation_coverage_pct = float(payload.get("automation_coverage_pct") or 0.0)
    acknowledgement_gap_count = int(payload.get("acknowledgement_gap_count") or 0)

    score = 58.0
    score += max(-16.0, min(14.0, (template_integrity_score - float(policy.get("min_template_integrity_score") or 88.0)) * 0.45))
    score += max(-18.0, min(16.0, (disclosure_completeness_pct - float(policy.get("min_disclosure_completeness_pct") or 90.0)) * 0.5))
    score += max(-12.0, min(12.0, (delivery_success_pct - float(policy.get("min_delivery_success_pct") or 92.0)) * 0.35))
    score += max(-14.0, min(8.0, (float(policy.get("max_staleness_hours") or 48.0) - report_staleness_hours) * 0.35))
    score += max(-12.0, min(12.0, (automation_coverage_pct - 85.0) * 0.25))
    score -= min(14.0, open_exceptions * 5.0)
    score -= min(8.0, acknowledgement_gap_count * 2.0)

    blockers = []
    needs_operator = False

    if policy.get("require_release_clear") and str((ctx.get("release") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("release posture blocked")
        score -= 14.0
    if str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("safety posture blocked")
        score -= 14.0
    if policy.get("require_delivery_ready") and not bool((ctx.get("delivery") or {}).get("investor_ready")):
        blockers.append("delivery system not investor ready")
        score -= 14.0
    if bool((ctx.get("delivery") or {}).get("blocked")):
        blockers.append("delivery currently blocked")
        score -= 10.0
    if policy.get("require_fund_admin_ready") and str((ctx.get("fund_admin") or {}).get("readiness") or "").lower() == "blocked":
        blockers.append("fund admin readiness blocked")
        score -= 14.0
    if policy.get("require_transparency_approved") and str((ctx.get("transparency") or {}).get("posture") or "").upper() not in {"APPROVED", "OPERATOR_REVIEW"}:
        blockers.append("investor transparency posture not approved")
        score -= 18.0
    if str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 12.0
    if bool((ctx.get("recovery") or {}).get("safe_mode")) or not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery posture not clear")
        score -= 14.0

    if template_integrity_score < float(policy.get("min_template_integrity_score") or 88.0):
        blockers.append("template integrity below threshold")
    if disclosure_completeness_pct < float(policy.get("min_disclosure_completeness_pct") or 90.0):
        blockers.append("disclosure completeness below threshold")
    if delivery_success_pct < float(policy.get("min_delivery_success_pct") or 92.0):
        blockers.append("delivery success below threshold")
    if report_staleness_hours > float(policy.get("max_staleness_hours") or 48.0):
        blockers.append("report staleness outside policy")
    if open_exceptions > int(policy.get("max_open_exceptions") or 1):
        blockers.append("too many open reporting exceptions")
    if acknowledgement_gap_count > 0 or (open_exceptions > 0 and bool(policy.get("require_operator_review_for_exceptions", True))):
        needs_operator = True

    approved = (score >= float(policy.get("min_automation_score") or 82.0)) and (len(blockers) == 0)
    posture = "APPROVED" if approved and not needs_operator else ("REVIEW" if len(blockers) == 0 else "BLOCKED")
    if needs_operator and approved:
        posture = "OPERATOR_REVIEW"

    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "approved": bool(approved and not needs_operator),
        "operator_review_required": bool(needs_operator),
        "posture": posture,
        "blockers": blockers,
        "recommended_schedule": payload.get("reporting_schedule") or "monthly-close+delivery",
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    ctx = _cross_system_context(email)
    runs = store.get("runs") or []
    exceptions = store.get("exceptions") or []
    latest = runs[0] if runs else {}
    latest_eval = latest.get("evaluation") or {}
    return {
        "reporting_disclosure_automation_status": {
            "posture": latest_eval.get("posture") or "UNCONFIGURED",
            "latest_score": latest_eval.get("score"),
            "run_count": len(runs),
            "exception_count": len(exceptions),
            "operator_review_required": bool(latest_eval.get("operator_review_required", False)),
        },
        "current_context": ctx,
        "latest_run": latest,
        "runs": runs[:20],
        "exceptions": exceptions[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.get("/api/reporting-disclosure-automation-layer/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/api/reporting-disclosure-automation-layer/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    ctx = _cross_system_context(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    result = _score_run(payload, ctx, policy)
    run = {
        "run_id": f"rda_{_now_ts()}",
        "created_at": _now_iso(),
        "reporting_schedule": payload.get("reporting_schedule") or "monthly-close+delivery",
        "payload": payload,
        "evaluation": result,
        "context": ctx,
    }
    _append(store, "runs", run, int(policy.get("retain_runs") or 180))
    _append(store, "automation_book", {
        "run_id": run["run_id"],
        "created_at": run["created_at"],
        "posture": result.get("posture"),
        "score": result.get("score"),
        "reporting_schedule": run["reporting_schedule"],
    }, int(policy.get("retain_runs") or 180))
    if result.get("blockers"):
        _append(store, "exceptions", {
            "exception_id": f"rda_exc_{_now_ts()}",
            "created_at": run["created_at"],
            "reporting_schedule": run["reporting_schedule"],
            "score": result.get("score"),
            "blockers": result.get("blockers"),
        }, int(policy.get("retain_runs") or 180))
    _save(email, store)
    return {"ok": True, "run": run, **_summary_for_email(email)}


@router.post("/api/reporting-disclosure-automation-layer/policy")
def update_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = dict(store.get("policy") or DEFAULT_POLICY)
    policy.update(payload or {})
    store["policy"] = policy
    _save(email, store)
    return {"ok": True, "policy": policy}


@router.post("/api/reporting-disclosure-automation-layer/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    payload = {
        "reporting_schedule": "monthly-close+delivery",
        "template_integrity_score": 93,
        "disclosure_completeness_pct": 95,
        "delivery_success_pct": 98,
        "report_staleness_hours": 18,
        "open_exceptions": 0,
        "automation_coverage_pct": 91,
        "acknowledgement_gap_count": 0,
    }
    ctx = _cross_system_context(email)
    result = _score_run(payload, ctx, store.get("policy") or dict(DEFAULT_POLICY))
    run = {
        "run_id": f"rda_demo_{_now_ts()}",
        "created_at": _now_iso(),
        "reporting_schedule": payload["reporting_schedule"],
        "payload": payload,
        "evaluation": result,
        "context": ctx,
    }
    _append(store, "runs", run, int((store.get("policy") or {}).get("retain_runs") or 180))
    _append(store, "automation_book", {
        "run_id": run["run_id"],
        "created_at": run["created_at"],
        "posture": result.get("posture"),
        "score": result.get("score"),
        "reporting_schedule": run["reporting_schedule"],
    }, int((store.get("policy") or {}).get("retain_runs") or 180))
    _save(email, store)
    return {"ok": True, **_summary_for_email(email)}
