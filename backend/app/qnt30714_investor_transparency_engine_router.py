from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["investor-transparency-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_transparency_engine"
DEFAULT_POLICY = {
    "retain_packets": 150,
    "min_transparency_score": 80.0,
    "min_disclosure_completeness_pct": 85.0,
    "min_explanation_coverage_pct": 80.0,
    "min_statement_accuracy_score": 82.0,
    "max_report_freshness_hours": 72.0,
    "min_acknowledgement_coverage_pct": 70.0,
    "require_forensic_clear": True,
    "require_recovery_clear": True,
    "require_delivery_ready": True,
    "require_fund_admin_ready": True,
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
            "packets": [],
            "exceptions": [],
            "disclosure_book": [],
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
            "pack_count": delivery.get("pack_count"),
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
    }


def _score_transparency(payload: dict, ctx: dict, policy: dict) -> dict:
    disclosure_completeness_pct = float(payload.get("disclosure_completeness_pct") or 0.0)
    explanation_coverage_pct = float(payload.get("explanation_coverage_pct") or 0.0)
    statement_accuracy_score = float(payload.get("statement_accuracy_score") or 0.0)
    report_freshness_hours = float(payload.get("report_freshness_hours") or 0.0)
    acknowledgement_coverage_pct = float(payload.get("acknowledgement_coverage_pct") or 0.0)
    delivery_success_pct = float(payload.get("delivery_success_pct") or 0.0)
    unresolved_exceptions = int(payload.get("unresolved_exceptions") or 0)

    score = 56.0
    score += max(-18.0, min(18.0, (disclosure_completeness_pct - float(policy.get("min_disclosure_completeness_pct") or 85.0)) * 0.6))
    score += max(-14.0, min(14.0, (explanation_coverage_pct - float(policy.get("min_explanation_coverage_pct") or 80.0)) * 0.5))
    score += max(-16.0, min(16.0, (statement_accuracy_score - float(policy.get("min_statement_accuracy_score") or 82.0)) * 0.55))
    score += max(-15.0, min(8.0, (float(policy.get("max_report_freshness_hours") or 72.0) - report_freshness_hours) * 0.3))
    score += max(-10.0, min(10.0, (acknowledgement_coverage_pct - float(policy.get("min_acknowledgement_coverage_pct") or 70.0)) * 0.35))
    score += max(-8.0, min(10.0, (delivery_success_pct - 85.0) * 0.2))
    score -= min(16.0, unresolved_exceptions * 4.0)

    blockers = []
    needs_operator = False

    if policy.get("require_forensic_clear") and str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 18.0
    if policy.get("require_recovery_clear") and bool((ctx.get("recovery") or {}).get("safe_mode")):
        blockers.append("recovery safe mode active")
        score -= 18.0
    if policy.get("require_recovery_clear") and not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery state not validated")
        score -= 14.0
    if policy.get("require_delivery_ready") and not bool((ctx.get("delivery") or {}).get("investor_ready")):
        blockers.append("delivery system not investor ready")
        score -= 16.0
    if bool((ctx.get("delivery") or {}).get("blocked")):
        blockers.append("delivery currently blocked")
        score -= 12.0
    if policy.get("require_fund_admin_ready") and str((ctx.get("fund_admin") or {}).get("readiness") or "").lower() == "blocked":
        blockers.append("fund admin readiness blocked")
        score -= 14.0
    if str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("safety posture blocked")
        score -= 14.0

    if disclosure_completeness_pct < float(policy.get("min_disclosure_completeness_pct") or 85.0):
        blockers.append("disclosure completeness below threshold")
    if explanation_coverage_pct < float(policy.get("min_explanation_coverage_pct") or 80.0):
        blockers.append("explanation coverage below threshold")
    if statement_accuracy_score < float(policy.get("min_statement_accuracy_score") or 82.0):
        blockers.append("statement accuracy below threshold")
    if report_freshness_hours > float(policy.get("max_report_freshness_hours") or 72.0):
        blockers.append("report freshness outside policy")
    if acknowledgement_coverage_pct < float(policy.get("min_acknowledgement_coverage_pct") or 70.0):
        needs_operator = True
    if unresolved_exceptions > 0 and bool(policy.get("require_operator_review_for_exceptions", True)):
        needs_operator = True

    approved = (score >= float(policy.get("min_transparency_score") or 80.0)) and (len(blockers) == 0)
    posture = "APPROVED" if approved and not needs_operator else ("REVIEW" if len(blockers) == 0 else "BLOCKED")
    if needs_operator and approved:
        posture = "OPERATOR_REVIEW"

    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "approved": bool(approved and not needs_operator),
        "operator_review_required": bool(needs_operator),
        "posture": posture,
        "blockers": blockers,
        "recommended_delivery_mode": payload.get("delivery_mode") or "institutional-monthly",
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    ctx = _cross_system_context(email)
    packets = store.get("packets") or []
    exceptions = store.get("exceptions") or []
    latest = packets[0] if packets else {}
    latest_eval = latest.get("evaluation") or {}
    posture = latest_eval.get("posture") or "WATCH"
    if bool((ctx.get("recovery") or {}).get("safe_mode")):
        posture = "SAFE_MODE"
    elif str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        posture = "BLOCKED"
    return {
        "mission": "QNT30714",
        "investor_transparency_status": {
            "posture": posture,
            "latest_score": latest_eval.get("score"),
            "approved": latest_eval.get("approved"),
            "operator_review_required": latest_eval.get("operator_review_required"),
            "packet_count": len(packets),
            "exception_count": len(exceptions),
            "delivery_mode": latest.get("delivery_mode"),
        },
        "latest_packet": latest,
        "current_context": ctx,
        "packets": packets[:25],
        "exceptions": exceptions[:25],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.get("/api/investor-transparency-engine/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/api/investor-transparency-engine/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_transparency(payload, ctx, policy)
    packet = {
        "packet_id": f"transparency-{_now_ts()}",
        "created_at": _now_iso(),
        "delivery_mode": payload.get("delivery_mode") or evaluation.get("recommended_delivery_mode"),
        "disclosure_completeness_pct": float(payload.get("disclosure_completeness_pct") or 0.0),
        "explanation_coverage_pct": float(payload.get("explanation_coverage_pct") or 0.0),
        "statement_accuracy_score": float(payload.get("statement_accuracy_score") or 0.0),
        "report_freshness_hours": float(payload.get("report_freshness_hours") or 0.0),
        "acknowledgement_coverage_pct": float(payload.get("acknowledgement_coverage_pct") or 0.0),
        "delivery_success_pct": float(payload.get("delivery_success_pct") or 0.0),
        "unresolved_exceptions": int(payload.get("unresolved_exceptions") or 0),
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "packets", packet, int(policy.get("retain_packets") or 150))
    if evaluation.get("posture") in ("BLOCKED", "OPERATOR_REVIEW"):
        _append(store, "exceptions", {
            "exception_id": f"transparency-exception-{_now_ts()}",
            "created_at": _now_iso(),
            "delivery_mode": packet["delivery_mode"],
            "score": evaluation.get("score"),
            "blockers": evaluation.get("blockers") or [],
            "operator_review_required": evaluation.get("operator_review_required"),
        }, int(policy.get("retain_packets") or 150))
    _append(store, "disclosure_book", {
        "entry_id": f"transparency-book-{_now_ts()}",
        "created_at": _now_iso(),
        "delivery_mode": packet["delivery_mode"],
        "posture": evaluation.get("posture"),
        "score": evaluation.get("score"),
    }, int(policy.get("retain_packets") or 150))
    _save(email, store)
    return {"ok": True, "packet": packet, "summary": _summary_for_email(email)}


@router.post("/api/investor-transparency-engine/policy")
def update_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    for key in DEFAULT_POLICY:
        if key in payload:
            policy[key] = payload[key]
    store["policy"] = policy
    _save(email, store)
    return {"ok": True, "policy": policy}


@router.post("/api/investor-transparency-engine/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    try:
        _delivery()._bootstrap_demo_for_email(email)
    except Exception:
        pass
    try:
        _fund_admin()._bootstrap_demo_for_email(email)
    except Exception:
        pass
    payload = {
        "delivery_mode": "institutional-monthly",
        "disclosure_completeness_pct": 91.0,
        "explanation_coverage_pct": 88.0,
        "statement_accuracy_score": 90.0,
        "report_freshness_hours": 24.0,
        "acknowledgement_coverage_pct": 76.0,
        "delivery_success_pct": 96.0,
        "unresolved_exceptions": 0,
    }
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_transparency(payload, ctx, policy)
    packet = {
        "packet_id": f"transparency-{_now_ts()}",
        "created_at": _now_iso(),
        **payload,
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "packets", packet, int(policy.get("retain_packets") or 150))
    _save(email, store)
    return _summary_for_email(email)
