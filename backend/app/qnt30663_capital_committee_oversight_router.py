from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["capital-committee-oversight-mesh"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
COMMITTEE_DIR = ARTIFACTS_DIR / "capital_committee_oversight_mesh"

DEFAULT_POLICY = {
    "priority_case_count": 8,
    "minimum_committee_readiness_score": 84.0,
    "minimum_release_authority_score": 80.0,
    "minimum_compliance_alignment_score": 78.0,
    "minimum_treasury_alignment_score": 74.0,
    "maximum_escalation_pressure_score": 26.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _execution_governance():
    from backend.app import qnt30662_execution_governance_command_router as governance
    return governance


def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as compliance
    return compliance


def _treasury():
    from backend.app import qnt30655_sovereign_treasury_router as treasury
    return treasury


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    COMMITTEE_DIR.mkdir(parents=True, exist_ok=True)
    return COMMITTEE_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round_money(v) -> float:
    return round(float(v or 0.0), 2)


def _round_pct(v) -> float:
    return round(float(v or 0.0), 4)


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "runs": [],
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


def _safe_summary(builder, *args, fallback: dict):
    try:
        return builder(*args)
    except Exception:
        return dict(fallback)


def _committee_book(dependencies: dict, policy: dict) -> list[dict]:
    governance = dependencies["governance"]
    compliance = dependencies["compliance"]
    treasury = dependencies["treasury"]
    strategic = dependencies["strategic"]
    queue = governance.get("command_queue") or []
    book = governance.get("governance_book") or []
    compliance_matrix = compliance.get("release_matrix") or []
    treasury_routes = treasury.get("funding_routes") or []
    treasury_grid = treasury.get("settlement_grid") or []
    directives = strategic.get("capital_directives") or []
    base_count = max(int(policy.get("priority_case_count") or 8), 4)
    base_len = max(len(queue), len(book), 1)
    out = []
    for idx in range(min(base_count, max(base_len, base_count))):
        q = queue[idx % max(len(queue), 1)] if queue else {}
        b = book[idx % max(len(book), 1)] if book else {}
        c = compliance_matrix[idx % max(len(compliance_matrix), 1)] if compliance_matrix else {}
        r = treasury_routes[idx % max(len(treasury_routes), 1)] if treasury_routes else {}
        g = treasury_grid[idx % max(len(treasury_grid), 1)] if treasury_grid else {}
        d = directives[idx % max(len(directives), 1)] if directives else {}
        committee_readiness = min(100.0,
            float(b.get("governance_score") or 0.0) * 0.24 +
            float(b.get("supervisory_score") or 0.0) * 0.16 +
            float(c.get("release_score") or 0.0) * 0.18 +
            float(r.get("route_readiness_score") or 0.0) * 0.16 +
            float(g.get("settlement_readiness_score") or 0.0) * 0.12 +
            (float(d.get("confidence") or 0.75) * 100.0) * 0.08 +
            6.0
        )
        release_authority = min(100.0,
            committee_readiness * 0.44 +
            float(c.get("release_score") or 0.0) * 0.18 +
            float(r.get("reserve_coverage_score") or 0.0) * 0.14 +
            float(g.get("settlement_readiness_score") or 0.0) * 0.10 +
            6.0
        )
        compliance_alignment = min(100.0,
            float(c.get("release_score") or 0.0) * 0.52 +
            committee_readiness * 0.18 +
            (82.0 if c.get("release_status") == "release" else 70.0 if c.get("release_status") == "monitor" else 58.0) * 0.16 +
            6.0
        )
        treasury_alignment = min(100.0,
            float(r.get("route_readiness_score") or 0.0) * 0.38 +
            float(r.get("reserve_coverage_score") or 0.0) * 0.18 +
            float(g.get("settlement_readiness_score") or 0.0) * 0.18 +
            committee_readiness * 0.14 +
            6.0
        )
        escalation_pressure = max(4.0,
            38.0 - committee_readiness * 0.14 - release_authority * 0.10 - compliance_alignment * 0.05 - treasury_alignment * 0.05 + idx * 0.7
        )
        status = "advance"
        if compliance_alignment < float(policy.get("minimum_compliance_alignment_score") or 78.0) or treasury_alignment < float(policy.get("minimum_treasury_alignment_score") or 74.0):
            status = "review"
        if release_authority < float(policy.get("minimum_release_authority_score") or 80.0) or escalation_pressure > float(policy.get("maximum_escalation_pressure_score") or 26.0) or q.get("queue_status") == "halt":
            status = "escalate"
        out.append({
            "case_id": f"cco_{idx+1:02d}",
            "allocator_name": q.get("allocator_name") or b.get("allocator_name") or f"Allocator {idx+1}",
            "strategy_id": q.get("strategy_id") or b.get("strategy_id") or d.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "product_id": b.get("product_id") or c.get("product_id") or f"QNT_CASE_{idx+1:02d}",
            "governance_status": b.get("command_status") or "approve",
            "committee_readiness_score": _round_pct(committee_readiness),
            "release_authority_score": _round_pct(release_authority),
            "compliance_alignment_score": _round_pct(compliance_alignment),
            "treasury_alignment_score": _round_pct(treasury_alignment),
            "escalation_pressure_score": _round_pct(escalation_pressure),
            "committee_status": status,
        })
    return out


def _oversight_lanes(book: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane_score = min(100.0,
            float(row.get("committee_readiness_score") or 0.0) * 0.34 +
            float(row.get("release_authority_score") or 0.0) * 0.24 +
            float(row.get("compliance_alignment_score") or 0.0) * 0.14 +
            float(row.get("treasury_alignment_score") or 0.0) * 0.14 +
            6.0
        )
        out.append({
            "lane_id": f"col_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "oversight_window": "capital committee release cycle",
            "committee_lane_score": _round_pct(lane_score),
            "lane_status": "greenlight" if lane_score >= float(policy.get("minimum_committee_readiness_score") or 84.0) and row.get("committee_status") == "advance" else ("hold" if row.get("committee_status") == "escalate" else "review"),
        })
    return out


def _authority_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority_score = min(100.0,
            float(row.get("committee_readiness_score") or 0.0) * 0.32 +
            float(row.get("release_authority_score") or 0.0) * 0.22 +
            float(row.get("compliance_alignment_score") or 0.0) * 0.16 +
            float(row.get("treasury_alignment_score") or 0.0) * 0.10 +
            float(lane.get("committee_lane_score") or 0.0) * 0.12 +
            4.0
        )
        authority_status = "release" if authority_score >= float(policy.get("minimum_release_authority_score") or 80.0) and lane.get("lane_status") == "greenlight" and row.get("committee_status") == "advance" else ("hold" if row.get("committee_status") == "escalate" else "review")
        out.append({
            "matrix_id": f"com_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "authority_release_score": _round_pct(authority_score),
            "authority_status": authority_status,
        })
    return out


def _committee_queue(book: list[dict], lanes: list[dict], matrix: list[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority = matrix[idx % max(len(matrix), 1)] if matrix else {}
        status = "approve"
        if authority.get("authority_status") == "review" or lane.get("lane_status") == "review" or row.get("committee_status") == "review":
            status = "review"
        if authority.get("authority_status") == "hold" or row.get("committee_status") == "escalate":
            status = "escalate"
        next_action = "approve committee release and maintain governed live execution oversight"
        if status == "review":
            next_action = "request committee memo refresh, compliance reconfirmation, and treasury reserve validation"
        if status == "escalate":
            next_action = "escalate to capital committee, freeze release authority, and require remediation package"
        out.append({
            "queue_id": f"coq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "next_action": next_action,
            "owner": "Capital Committee",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, book: list[dict], lanes: list[dict], matrix: list[dict], queue: list[dict]) -> dict:
    governance_overview = dependencies["governance"].get("execution_governance_overview") or {}
    total_capital = float(governance_overview.get("governed_capital_millions") or 0.0)
    approve_count = len([x for x in queue if x.get("queue_status") == "approve"])
    review_count = len([x for x in queue if x.get("queue_status") == "review"])
    escalate_count = len([x for x in queue if x.get("queue_status") == "escalate"])
    release_count = len([x for x in matrix if x.get("authority_status") == "release"])
    avg_readiness = sum(float(x.get("committee_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_authority = sum(float(x.get("release_authority_score") or 0.0) for x in book) / max(len(book), 1)
    avg_compliance = sum(float(x.get("compliance_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_treasury = sum(float(x.get("treasury_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_pressure = sum(float(x.get("escalation_pressure_score") or 0.0) for x in book) / max(len(book), 1)
    score = min(100.0,
        avg_readiness * 0.28 + avg_authority * 0.22 + avg_compliance * 0.16 + avg_treasury * 0.12 + (100.0 - avg_pressure) * 0.10 + float(governance_overview.get("execution_governance_score") or 74.0) * 0.08
    )
    posture = "capital-committee-oversight-ready"
    if escalate_count:
        posture = "capital-committee-oversight-constrained"
    elif review_count > approve_count:
        posture = "capital-committee-oversight-reviewing"
    return {
        "committee_governed_capital_millions": _round_money(total_capital),
        "approve_count": approve_count,
        "review_count": review_count,
        "escalate_count": escalate_count,
        "release_ready_count": release_count,
        "average_committee_readiness": _round_pct(avg_readiness),
        "average_release_authority": _round_pct(avg_authority),
        "average_compliance_alignment": _round_pct(avg_compliance),
        "average_treasury_alignment": _round_pct(avg_treasury),
        "average_escalation_pressure": _round_pct(avg_pressure),
        "committee_oversight_score": _round_pct(score),
        "committee_oversight_posture": posture,
        "execution_governance_posture": governance_overview.get("execution_governance_posture"),
    }


def _actions(overview: dict, queue: list[dict], matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("committee_oversight_posture") != "capital-committee-oversight-ready":
        actions.append("Tighten committee release authority and require refreshed evidence packs before widening capital authorization.")
    approvals = [x for x in queue if x.get("queue_status") == "approve"][:3]
    if approvals:
        actions.append("Approve committee release for " + ", ".join(x.get("allocator_name") for x in approvals) + ".")
    reviews = [x for x in queue if x.get("queue_status") == "review"]
    if reviews:
        actions.append(f"Review {len(reviews)} committee cases for compliance alignment and treasury sufficiency before live expansion.")
    escalations = [x for x in matrix if x.get("authority_status") == "hold"]
    if escalations:
        actions.append("Escalate release hold package for " + ", ".join(x.get("allocator_name") for x in escalations[:2]) + ".")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    governance = _safe_summary(_execution_governance()._build_summary, email, fallback={
        "execution_governance_overview": {"execution_governance_score": 74.0, "execution_governance_posture": "execution-governance-command-building", "governed_capital_millions": 0.0},
        "governance_book": [],
        "command_queue": [],
    })
    compliance = _safe_summary(_compliance()._build_summary, email, fallback={
        "institutional_compliance_overview": {"institutional_compliance_score": 76.0, "institutional_compliance_posture": "institutional-compliance-building"},
        "release_matrix": [],
    })
    treasury = _safe_summary(_treasury()._build_summary, email, fallback={
        "sovereign_treasury_overview": {"sovereign_treasury_score": 75.0, "sovereign_treasury_posture": "sovereign-treasury-building"},
        "funding_routes": [],
        "settlement_grid": [],
    })
    strategic = _safe_summary(_strategic()._build_summary, email, fallback={
        "confidence_score": 76.0,
        "capital_directives": [],
        "operating_posture": "strategic-building",
    })
    dependencies = {"governance": governance, "compliance": compliance, "treasury": treasury, "strategic": strategic}
    book = _committee_book(dependencies, policy)
    lanes = _oversight_lanes(book, policy)
    matrix = _authority_matrix(book, lanes, policy)
    queue = _committee_queue(book, lanes, matrix)
    overview = _overview(dependencies, book, lanes, matrix, queue)
    governance_overview = governance.get("execution_governance_overview") or {}
    compliance_overview = compliance.get("institutional_compliance_overview") or {}
    treasury_overview = treasury.get("sovereign_treasury_overview") or {}
    return {
        "mission": "QNT30663",
        "generated_at": _now_iso(),
        "policy": policy,
        "committee_oversight_overview": overview,
        "committee_book": book,
        "oversight_lanes": lanes,
        "authority_matrix": matrix,
        "committee_queue": queue,
        "committee_dependencies": {
            "execution_governance_posture": governance_overview.get("execution_governance_posture"),
            "execution_governance_score": governance_overview.get("execution_governance_score"),
            "institutional_compliance_posture": compliance_overview.get("institutional_compliance_posture"),
            "institutional_compliance_score": compliance_overview.get("institutional_compliance_score"),
            "sovereign_treasury_posture": treasury_overview.get("sovereign_treasury_posture"),
            "sovereign_treasury_score": treasury_overview.get("sovereign_treasury_score"),
            "strategic_posture": strategic.get("operating_posture"),
            "strategic_score": strategic.get("confidence_score"),
        },
        "committee_actions": _actions(overview, queue, matrix),
    }


@router.get("/api/capital-committee-oversight-mesh/summary")
def capital_committee_oversight_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/capital-committee-oversight-mesh/run")
def capital_committee_oversight_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("committee_oversight_overview") or {}
    run = {
        "run_id": f"cco_{time.time_ns()}",
        "mission": "QNT30663",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "committee_oversight_posture": overview.get("committee_oversight_posture"),
        "committee_oversight_score": overview.get("committee_oversight_score"),
        "approve_count": overview.get("approve_count"),
        "escalate_count": overview.get("escalate_count"),
        "committee_governed_capital_millions": overview.get("committee_governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/capital-committee-oversight-mesh/audit")
def capital_committee_oversight_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30663",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/capital-committee-oversight-mesh/policy")
def capital_committee_oversight_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    allowed = set(DEFAULT_POLICY.keys())
    for key, value in payload.items():
        if key in allowed:
            policy[key] = value
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy, "summary": _build_summary(email)}
