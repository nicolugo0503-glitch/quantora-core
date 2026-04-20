from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["allocation-oversight-fabric"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
FABRIC_DIR = ARTIFACTS_DIR / "allocation_oversight_fabric"

DEFAULT_POLICY = {
    "priority_oversight_case_count": 8,
    "minimum_oversight_readiness_score": 86.0,
    "minimum_oversight_authority_score": 84.0,
    "minimum_committee_alignment_score": 81.0,
    "minimum_governance_alignment_score": 80.0,
    "maximum_oversight_stress_score": 23.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _allocation_control():
    from backend.app import qnt30666_live_allocation_control_tower_router as mod
    return mod


def _committee():
    from backend.app import qnt30663_capital_committee_oversight_router as mod
    return mod


def _governance():
    from backend.app import qnt30662_execution_governance_command_router as mod
    return mod


def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as mod
    return mod


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    FABRIC_DIR.mkdir(parents=True, exist_ok=True)
    return FABRIC_DIR / f"{_safe(email)}.json"


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


def _oversight_book(dependencies: dict, policy: dict) -> list[dict]:
    control = dependencies["allocation_control"]
    committee = dependencies["committee"]
    governance = dependencies["governance"]
    compliance = dependencies["compliance"]
    allocation_book = control.get("allocation_book") or []
    allocation_matrix = control.get("allocation_matrix") or []
    allocation_queue = control.get("allocation_queue") or []
    committee_book = committee.get("committee_book") or []
    authority_matrix = committee.get("authority_matrix") or []
    command_matrix = governance.get("command_matrix") or []
    priority_count = max(int(policy.get("priority_oversight_case_count") or 8), 4)
    base_len = max(len(allocation_book), len(committee_book), len(authority_matrix), len(command_matrix), 1)
    release_matrix = compliance.get("release_matrix") or []
    out = []
    for idx in range(min(priority_count, max(base_len, priority_count))):
        ab = allocation_book[idx % max(len(allocation_book), 1)] if allocation_book else {}
        am = allocation_matrix[idx % max(len(allocation_matrix), 1)] if allocation_matrix else {}
        aq = allocation_queue[idx % max(len(allocation_queue), 1)] if allocation_queue else {}
        cb = committee_book[idx % max(len(committee_book), 1)] if committee_book else {}
        au = authority_matrix[idx % max(len(authority_matrix), 1)] if authority_matrix else {}
        cm = command_matrix[idx % max(len(command_matrix), 1)] if command_matrix else {}
        rm = release_matrix[idx % max(len(release_matrix), 1)] if release_matrix else {}
        readiness = min(100.0,
            float(ab.get("allocation_readiness_score") or 0.0) * 0.28 +
            float(am.get("allocation_authority_score") or 0.0) * 0.18 +
            float(au.get("authority_score") or 0.0) * 0.14 +
            float(cm.get("command_score") or 0.0) * 0.12 +
            float(rm.get("release_authority_score") or 0.0) * 0.08 +
            7.0
        )
        authority = min(100.0,
            readiness * 0.34 +
            float(au.get("authority_score") or 0.0) * 0.22 +
            float(cm.get("command_score") or 0.0) * 0.16 +
            5.0
        )
        committee_alignment = min(100.0,
            float(au.get("authority_score") or 0.0) * 0.38 +
            float(cb.get("committee_readiness_score") or 0.0) * 0.22 +
            8.0
        )
        governance_alignment = min(100.0,
            float(cm.get("command_score") or 0.0) * 0.42 +
            float(ab.get("execution_alignment_score") or 0.0) * 0.18 +
            float(rm.get("release_authority_score") or 0.0) * 0.10 +
            7.0
        )
        stress = max(4.0, 34.0 - readiness * 0.13 - authority * 0.10 - committee_alignment * 0.08 - governance_alignment * 0.06 + idx * 0.55)
        status = "approve"
        if committee_alignment < float(policy.get("minimum_committee_alignment_score") or 81.0) or governance_alignment < float(policy.get("minimum_governance_alignment_score") or 80.0):
            status = "review"
        if authority < float(policy.get("minimum_oversight_authority_score") or 84.0) or stress > float(policy.get("maximum_oversight_stress_score") or 23.0) or aq.get("queue_status") == "hold":
            status = "hold"
        out.append({
            "oversight_case_id": f"aof_{idx+1:02d}",
            "allocator_name": ab.get("allocator_name") or cb.get("allocator_name") or f"Allocator {idx+1}",
            "strategy_id": ab.get("strategy_id") or cb.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "product_id": ab.get("product_id") or cb.get("product_id") or f"QNT_AOF_{idx+1:02d}",
            "jurisdiction": ab.get("jurisdiction") or cb.get("jurisdiction") or "multi-jurisdiction",
            "capital_target_millions": _round_money(ab.get("capital_target_millions") or 0.0),
            "oversight_readiness_score": _round_pct(readiness),
            "oversight_authority_score": _round_pct(authority),
            "committee_alignment_score": _round_pct(committee_alignment),
            "governance_alignment_score": _round_pct(governance_alignment),
            "oversight_stress_score": _round_pct(stress),
            "oversight_status": status,
        })
    return out


def _oversight_lanes(book: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane_score = min(100.0,
            float(row.get("oversight_readiness_score") or 0.0) * 0.34 +
            float(row.get("oversight_authority_score") or 0.0) * 0.24 +
            float(row.get("committee_alignment_score") or 0.0) * 0.12 +
            float(row.get("governance_alignment_score") or 0.0) * 0.12 +
            6.0
        )
        status = "greenlight" if lane_score >= float(policy.get("minimum_oversight_readiness_score") or 86.0) and row.get("oversight_status") == "approve" else ("hold" if row.get("oversight_status") == "hold" else "review")
        out.append({
            "lane_id": f"aol_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "oversight_window": "allocation oversight review window",
            "oversight_lane_score": _round_pct(lane_score),
            "lane_status": status,
        })
    return out


def _oversight_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority_score = min(100.0,
            float(row.get("oversight_readiness_score") or 0.0) * 0.28 +
            float(row.get("oversight_authority_score") or 0.0) * 0.28 +
            float(row.get("committee_alignment_score") or 0.0) * 0.12 +
            float(row.get("governance_alignment_score") or 0.0) * 0.12 +
            float(lane.get("oversight_lane_score") or 0.0) * 0.12 +
            4.0
        )
        status = "approve" if authority_score >= float(policy.get("minimum_oversight_authority_score") or 84.0) and lane.get("lane_status") == "greenlight" and row.get("oversight_status") == "approve" else ("hold" if row.get("oversight_status") == "hold" else "review")
        out.append({
            "matrix_id": f"aom_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "oversight_authority_score": _round_pct(authority_score),
            "oversight_authority_status": status,
        })
    return out


def _oversight_queue(book: list[dict], lanes: list[dict], matrix: list[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority = matrix[idx % max(len(matrix), 1)] if matrix else {}
        status = "approve"
        if authority.get("oversight_authority_status") == "review" or lane.get("lane_status") == "review" or row.get("oversight_status") == "review":
            status = "review"
        if authority.get("oversight_authority_status") == "hold" or row.get("oversight_status") == "hold":
            status = "hold"
        next_action = "approve continued live allocation supervision and keep the case inside governed scaling lanes"
        if status == "review":
            next_action = "refresh committee fit, governance evidence, and compliance posture before additional live allocation"
        if status == "hold":
            next_action = "freeze further scaling, escalate allocation case, and block downstream deployment expansion"
        out.append({
            "queue_id": f"aoq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "next_action": next_action,
            "owner": "Allocation Oversight Fabric",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, book: list[dict], lanes: list[dict], matrix: list[dict], queue: list[dict]) -> dict:
    control_overview = dependencies["allocation_control"].get("live_allocation_control_overview") or {}
    committee_overview = dependencies["committee"].get("committee_oversight_overview") or {}
    governance_overview = dependencies["governance"].get("execution_governance_overview") or {}
    compliance_overview = dependencies["compliance"].get("institutional_compliance_overview") or {}
    total_capital = sum(float(x.get("capital_target_millions") or 0.0) for x in book)
    approve_count = len([x for x in queue if x.get("queue_status") == "approve"])
    review_count = len([x for x in queue if x.get("queue_status") == "review"])
    hold_count = len([x for x in queue if x.get("queue_status") == "hold"])
    green_count = len([x for x in lanes if x.get("lane_status") == "greenlight"])
    avg_readiness = sum(float(x.get("oversight_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_authority = sum(float(x.get("oversight_authority_score") or 0.0) for x in book) / max(len(book), 1)
    avg_committee = sum(float(x.get("committee_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_governance = sum(float(x.get("governance_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_stress = sum(float(x.get("oversight_stress_score") or 0.0) for x in book) / max(len(book), 1)
    score = min(100.0,
        avg_readiness * 0.26 + avg_authority * 0.22 + avg_committee * 0.14 + avg_governance * 0.12 + (100.0 - avg_stress) * 0.12 + float(governance_overview.get("execution_governance_score") or 76.0) * 0.08 + float(control_overview.get("live_allocation_control_score") or 78.0) * 0.06
    )
    posture = "allocation-oversight-ready"
    if hold_count:
        posture = "allocation-oversight-constrained"
    elif review_count > approve_count:
        posture = "allocation-oversight-reviewing"
    return {
        "supervised_capital_millions": _round_money(total_capital),
        "approve_count": approve_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "greenlight_lane_count": green_count,
        "average_oversight_readiness": _round_pct(avg_readiness),
        "average_oversight_authority": _round_pct(avg_authority),
        "average_committee_alignment": _round_pct(avg_committee),
        "average_governance_alignment": _round_pct(avg_governance),
        "average_oversight_stress": _round_pct(avg_stress),
        "allocation_oversight_score": _round_pct(score),
        "allocation_oversight_posture": posture,
        "live_allocation_control_posture": control_overview.get("live_allocation_control_posture"),
        "capital_committee_oversight_posture": committee_overview.get("capital_committee_oversight_posture"),
        "execution_governance_posture": governance_overview.get("execution_governance_posture"),
        "institutional_compliance_posture": compliance_overview.get("institutional_compliance_posture"),
    }


def _actions(overview: dict, queue: list[dict], matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("allocation_oversight_posture") != "allocation-oversight-ready":
        actions.append("Tighten committee, governance, and compliance supervision before increasing live allocation velocity.")
    approves = [x for x in queue if x.get("queue_status") == "approve"][:3]
    if approves:
        actions.append("Approve oversight passage for " + ", ".join(x.get("allocator_name") for x in approves) + ".")
    reviews = [x for x in queue if x.get("queue_status") == "review"]
    if reviews:
        actions.append(f"Review {len(reviews)} allocation oversight cases before any additional scale-up.")
    holds = [x for x in matrix if x.get("oversight_authority_status") == "hold"]
    if holds:
        actions.append("Hold oversight package for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    control = _safe_summary(_allocation_control()._build_summary, email, fallback={
        "live_allocation_control_overview": {"live_allocation_control_score": 76.0, "live_allocation_control_posture": "live-allocation-control-building"},
        "allocation_book": [],
        "allocation_matrix": [],
        "allocation_queue": [],
    })
    committee = _safe_summary(_committee()._build_summary, email, fallback={
        "committee_oversight_overview": {"capital_committee_oversight_score": 74.0, "capital_committee_oversight_posture": "capital-committee-oversight-building"},
        "committee_book": [],
        "authority_matrix": [],
        "committee_queue": [],
    })
    governance = _safe_summary(_governance()._build_summary, email, fallback={
        "execution_governance_overview": {"execution_governance_score": 75.0, "execution_governance_posture": "execution-governance-building"},
        "command_matrix": [],
        "command_queue": [],
    })
    compliance = _safe_summary(_compliance()._build_summary, email, fallback={
        "institutional_compliance_overview": {"institutional_compliance_score": 77.0, "institutional_compliance_posture": "institutional-compliance-building"},
        "release_matrix": [],
    })
    dependencies = {"allocation_control": control, "committee": committee, "governance": governance, "compliance": compliance}
    book = _oversight_book(dependencies, policy)
    lanes = _oversight_lanes(book, policy)
    matrix = _oversight_matrix(book, lanes, policy)
    queue = _oversight_queue(book, lanes, matrix)
    overview = _overview(dependencies, book, lanes, matrix, queue)
    return {
        "mission": "QNT30667",
        "generated_at": _now_iso(),
        "policy": policy,
        "allocation_oversight_overview": overview,
        "oversight_book": book,
        "oversight_lanes": lanes,
        "oversight_matrix": matrix,
        "oversight_queue": queue,
        "oversight_dependencies": {
            "live_allocation_control_posture": (control.get("live_allocation_control_overview") or {}).get("live_allocation_control_posture"),
            "live_allocation_control_score": (control.get("live_allocation_control_overview") or {}).get("live_allocation_control_score"),
            "capital_committee_oversight_posture": (committee.get("committee_oversight_overview") or {}).get("capital_committee_oversight_posture"),
            "capital_committee_oversight_score": (committee.get("committee_oversight_overview") or {}).get("capital_committee_oversight_score"),
            "execution_governance_posture": (governance.get("execution_governance_overview") or {}).get("execution_governance_posture"),
            "execution_governance_score": (governance.get("execution_governance_overview") or {}).get("execution_governance_score"),
            "institutional_compliance_posture": (compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_posture"),
            "institutional_compliance_score": (compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_score"),
        },
        "oversight_actions": _actions(overview, queue, matrix),
    }


@router.get("/api/allocation-oversight-fabric/summary")
def allocation_oversight_fabric_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/allocation-oversight-fabric/run")
def allocation_oversight_fabric_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("allocation_oversight_overview") or {}
    run = {
        "run_id": f"aof_{time.time_ns()}",
        "mission": "QNT30667",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "allocation_oversight_posture": overview.get("allocation_oversight_posture"),
        "allocation_oversight_score": overview.get("allocation_oversight_score"),
        "approve_count": overview.get("approve_count"),
        "hold_count": overview.get("hold_count"),
        "supervised_capital_millions": overview.get("supervised_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/allocation-oversight-fabric/audit")
def allocation_oversight_fabric_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30667",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/allocation-oversight-fabric/policy")
def allocation_oversight_fabric_policy(payload: dict = Body(...)):
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
