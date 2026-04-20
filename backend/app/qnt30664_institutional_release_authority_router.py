from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["institutional-release-authority-grid"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
RELEASE_DIR = ARTIFACTS_DIR / "institutional_release_authority_grid"

DEFAULT_POLICY = {
    "priority_release_case_count": 8,
    "minimum_release_readiness_score": 85.0,
    "minimum_authority_clearance_score": 82.0,
    "minimum_committee_alignment_score": 80.0,
    "minimum_mobility_alignment_score": 76.0,
    "maximum_release_friction_score": 24.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _committee():
    from backend.app import qnt30663_capital_committee_oversight_router as committee
    return committee


def _activation():
    from backend.app import qnt30660_post_close_activation_router as activation
    return activation


def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as compliance
    return compliance


def _mobility():
    from backend.app import qnt30656_capital_mobility_router as mobility
    return mobility


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    return RELEASE_DIR / f"{_safe(email)}.json"


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


def _release_book(dependencies: dict, policy: dict) -> list[dict]:
    committee = dependencies["committee"]
    activation = dependencies["activation"]
    compliance = dependencies["compliance"]
    mobility = dependencies["mobility"]
    queue = committee.get("committee_queue") or []
    authority = committee.get("authority_matrix") or []
    cases = committee.get("committee_book") or []
    activation_queue = activation.get("activation_queue") or []
    release_matrix = compliance.get("release_matrix") or []
    transfer_queue = mobility.get("transfer_queue") or []
    corridor = mobility.get("mobility_corridors") or []
    base_count = max(int(policy.get("priority_release_case_count") or 8), 4)
    base_len = max(len(queue), len(authority), len(cases), 1)
    out = []
    for idx in range(min(base_count, max(base_len, base_count))):
        q = queue[idx % max(len(queue), 1)] if queue else {}
        a = authority[idx % max(len(authority), 1)] if authority else {}
        c = cases[idx % max(len(cases), 1)] if cases else {}
        pq = activation_queue[idx % max(len(activation_queue), 1)] if activation_queue else {}
        rm = release_matrix[idx % max(len(release_matrix), 1)] if release_matrix else {}
        tq = transfer_queue[idx % max(len(transfer_queue), 1)] if transfer_queue else {}
        co = corridor[idx % max(len(corridor), 1)] if corridor else {}
        release_readiness = min(100.0,
            float(c.get("committee_readiness_score") or 0.0) * 0.24 +
            float(a.get("authority_release_score") or 0.0) * 0.22 +
            float(rm.get("release_score") or 0.0) * 0.16 +
            float(co.get("mobility_readiness_score") or 0.0) * 0.12 +
            float(co.get("corridor_score") or 0.0) * 0.08 +
            (84.0 if pq.get("queue_status") == "launch" else 75.0 if pq.get("queue_status") == "prepare" else 61.0) * 0.10 +
            6.0
        )
        authority_clearance = min(100.0,
            release_readiness * 0.40 +
            float(a.get("authority_release_score") or 0.0) * 0.22 +
            float(rm.get("release_score") or 0.0) * 0.14 +
            float(co.get("mobility_readiness_score") or 0.0) * 0.10 +
            5.0
        )
        committee_alignment = min(100.0,
            float(c.get("release_authority_score") or 0.0) * 0.44 +
            float(c.get("committee_readiness_score") or 0.0) * 0.24 +
            float(a.get("authority_release_score") or 0.0) * 0.14 +
            5.0
        )
        mobility_alignment = min(100.0,
            float(co.get("mobility_readiness_score") or 0.0) * 0.42 +
            float(co.get("corridor_score") or 0.0) * 0.18 +
            float(co.get("passport_score") or 0.0) * 0.10 +
            float(release_readiness) * 0.10 +
            6.0
        )
        release_friction = max(4.0,
            34.0 - release_readiness * 0.12 - authority_clearance * 0.10 - committee_alignment * 0.06 - mobility_alignment * 0.05 + idx * 0.65
        )
        status = "release"
        if committee_alignment < float(policy.get("minimum_committee_alignment_score") or 80.0) or mobility_alignment < float(policy.get("minimum_mobility_alignment_score") or 76.0):
            status = "review"
        if authority_clearance < float(policy.get("minimum_authority_clearance_score") or 82.0) or release_friction > float(policy.get("maximum_release_friction_score") or 24.0) or q.get("queue_status") == "escalate" or tq.get("queue_status") == "hold":
            status = "hold"
        out.append({
            "release_case_id": f"rag_{idx+1:02d}",
            "allocator_name": c.get("allocator_name") or q.get("allocator_name") or a.get("allocator_name") or f"Allocator {idx+1}",
            "strategy_id": c.get("strategy_id") or q.get("strategy_id") or a.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "product_id": c.get("product_id") or a.get("product_id") or f"QNT_RELEASE_{idx+1:02d}",
            "jurisdiction": co.get("jurisdiction") or tq.get("jurisdiction") or "multi-jurisdiction",
            "release_readiness_score": _round_pct(release_readiness),
            "authority_clearance_score": _round_pct(authority_clearance),
            "committee_alignment_score": _round_pct(committee_alignment),
            "mobility_alignment_score": _round_pct(mobility_alignment),
            "release_friction_score": _round_pct(release_friction),
            "release_status": status,
        })
    return out


def _authority_lanes(book: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane_score = min(100.0,
            float(row.get("release_readiness_score") or 0.0) * 0.34 +
            float(row.get("authority_clearance_score") or 0.0) * 0.24 +
            float(row.get("committee_alignment_score") or 0.0) * 0.14 +
            float(row.get("mobility_alignment_score") or 0.0) * 0.12 +
            6.0
        )
        out.append({
            "lane_id": f"ral_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "release_window": "institutional release authority cycle",
            "authority_lane_score": _round_pct(lane_score),
            "lane_status": "greenlight" if lane_score >= float(policy.get("minimum_release_readiness_score") or 85.0) and row.get("release_status") == "release" else ("hold" if row.get("release_status") == "hold" else "review"),
        })
    return out


def _release_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release_score = min(100.0,
            float(row.get("release_readiness_score") or 0.0) * 0.30 +
            float(row.get("authority_clearance_score") or 0.0) * 0.24 +
            float(row.get("committee_alignment_score") or 0.0) * 0.14 +
            float(row.get("mobility_alignment_score") or 0.0) * 0.12 +
            float(lane.get("authority_lane_score") or 0.0) * 0.12 +
            4.0
        )
        release_authority_status = "release" if release_score >= float(policy.get("minimum_authority_clearance_score") or 82.0) and lane.get("lane_status") == "greenlight" and row.get("release_status") == "release" else ("hold" if row.get("release_status") == "hold" else "review")
        out.append({
            "matrix_id": f"ram_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "release_authority_score": _round_pct(release_score),
            "release_authority_status": release_authority_status,
        })
    return out


def _release_queue(book: list[dict], lanes: list[dict], matrix: list[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority = matrix[idx % max(len(matrix), 1)] if matrix else {}
        status = "release"
        if authority.get("release_authority_status") == "review" or lane.get("lane_status") == "review" or row.get("release_status") == "review":
            status = "review"
        if authority.get("release_authority_status") == "hold" or row.get("release_status") == "hold":
            status = "hold"
        next_action = "authorize governed institutional release and route capital into live deployment governance"
        if status == "review":
            next_action = "refresh committee evidence, reconfirm compliance release matrix, and validate corridor mobility"
        if status == "hold":
            next_action = "freeze institutional release authority and escalate remediation package before capital dispatch"
        out.append({
            "queue_id": f"raq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "next_action": next_action,
            "owner": "Institutional Release Authority",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, book: list[dict], lanes: list[dict], matrix: list[dict], queue: list[dict]) -> dict:
    committee_overview = dependencies["committee"].get("committee_oversight_overview") or {}
    activation_overview = dependencies["activation"].get("activation_overview") or {}
    total_capital = float(activation_overview.get("activation_ready_capital_millions") or committee_overview.get("committee_governed_capital_millions") or 0.0)
    release_count = len([x for x in queue if x.get("queue_status") == "release"])
    review_count = len([x for x in queue if x.get("queue_status") == "review"])
    hold_count = len([x for x in queue if x.get("queue_status") == "hold"])
    authority_ready_count = len([x for x in matrix if x.get("release_authority_status") == "release"])
    avg_readiness = sum(float(x.get("release_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_clearance = sum(float(x.get("authority_clearance_score") or 0.0) for x in book) / max(len(book), 1)
    avg_committee = sum(float(x.get("committee_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_mobility = sum(float(x.get("mobility_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_friction = sum(float(x.get("release_friction_score") or 0.0) for x in book) / max(len(book), 1)
    score = min(100.0,
        avg_readiness * 0.28 + avg_clearance * 0.22 + avg_committee * 0.14 + avg_mobility * 0.12 + (100.0 - avg_friction) * 0.12 + float(committee_overview.get("committee_oversight_score") or 76.0) * 0.08
    )
    posture = "institutional-release-authority-ready"
    if hold_count:
        posture = "institutional-release-authority-constrained"
    elif review_count > release_count:
        posture = "institutional-release-authority-reviewing"
    return {
        "release_governed_capital_millions": _round_money(total_capital),
        "release_count": release_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "authority_ready_count": authority_ready_count,
        "average_release_readiness": _round_pct(avg_readiness),
        "average_authority_clearance": _round_pct(avg_clearance),
        "average_committee_alignment": _round_pct(avg_committee),
        "average_mobility_alignment": _round_pct(avg_mobility),
        "average_release_friction": _round_pct(avg_friction),
        "institutional_release_authority_score": _round_pct(score),
        "institutional_release_authority_posture": posture,
        "committee_oversight_posture": committee_overview.get("committee_oversight_posture"),
    }


def _actions(overview: dict, queue: list[dict], matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("institutional_release_authority_posture") != "institutional-release-authority-ready":
        actions.append("Tighten institutional release authority and require refreshed governance packets before widening release lanes.")
    releases = [x for x in queue if x.get("queue_status") == "release"][:3]
    if releases:
        actions.append("Authorize release for " + ", ".join(x.get("allocator_name") for x in releases) + ".")
    reviews = [x for x in queue if x.get("queue_status") == "review"]
    if reviews:
        actions.append(f"Review {len(reviews)} release cases for committee alignment and mobility sufficiency before capital dispatch.")
    holds = [x for x in matrix if x.get("release_authority_status") == "hold"]
    if holds:
        actions.append("Hold release package for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    committee = _safe_summary(_committee()._build_summary, email, fallback={
        "committee_oversight_overview": {"committee_oversight_score": 76.0, "committee_oversight_posture": "capital-committee-building", "committee_governed_capital_millions": 0.0},
        "committee_book": [],
        "authority_matrix": [],
        "committee_queue": [],
    })
    activation = _safe_summary(_activation()._build_summary, email, fallback={
        "activation_overview": {"activation_score": 74.0, "activation_posture": "post-close-activation-building", "activation_ready_capital_millions": 0.0},
        "activation_queue": [],
    })
    compliance = _safe_summary(_compliance()._build_summary, email, fallback={
        "institutional_compliance_overview": {"institutional_compliance_score": 76.0, "institutional_compliance_posture": "institutional-compliance-building"},
        "release_matrix": [],
    })
    mobility = _safe_summary(_mobility()._build_summary, email, fallback={
        "capital_mobility_overview": {"capital_mobility_score": 75.0, "capital_mobility_posture": "capital-mobility-building"},
        "mobility_corridors": [],
        "transfer_queue": [],
    })
    dependencies = {"committee": committee, "activation": activation, "compliance": compliance, "mobility": mobility}
    book = _release_book(dependencies, policy)
    lanes = _authority_lanes(book, policy)
    matrix = _release_matrix(book, lanes, policy)
    queue = _release_queue(book, lanes, matrix)
    overview = _overview(dependencies, book, lanes, matrix, queue)
    committee_overview = committee.get("committee_oversight_overview") or {}
    activation_overview = activation.get("activation_overview") or {}
    compliance_overview = compliance.get("institutional_compliance_overview") or {}
    mobility_overview = mobility.get("capital_mobility_overview") or {}
    return {
        "mission": "QNT30664",
        "generated_at": _now_iso(),
        "policy": policy,
        "institutional_release_authority_overview": overview,
        "release_book": book,
        "authority_lanes": lanes,
        "release_matrix": matrix,
        "release_queue": queue,
        "release_dependencies": {
            "committee_oversight_posture": committee_overview.get("committee_oversight_posture"),
            "committee_oversight_score": committee_overview.get("committee_oversight_score"),
            "activation_posture": activation_overview.get("activation_posture"),
            "activation_score": activation_overview.get("activation_score"),
            "institutional_compliance_posture": compliance_overview.get("institutional_compliance_posture"),
            "institutional_compliance_score": compliance_overview.get("institutional_compliance_score"),
            "capital_mobility_posture": mobility_overview.get("capital_mobility_posture"),
            "capital_mobility_score": mobility_overview.get("capital_mobility_score"),
        },
        "release_actions": _actions(overview, queue, matrix),
    }


@router.get("/api/institutional-release-authority-grid/summary")
def institutional_release_authority_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/institutional-release-authority-grid/run")
def institutional_release_authority_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("institutional_release_authority_overview") or {}
    run = {
        "run_id": f"rag_{time.time_ns()}",
        "mission": "QNT30664",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "institutional_release_authority_posture": overview.get("institutional_release_authority_posture"),
        "institutional_release_authority_score": overview.get("institutional_release_authority_score"),
        "release_count": overview.get("release_count"),
        "hold_count": overview.get("hold_count"),
        "release_governed_capital_millions": overview.get("release_governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/institutional-release-authority-grid/audit")
def institutional_release_authority_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30664",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/institutional-release-authority-grid/policy")
def institutional_release_authority_policy(payload: dict = Body(...)):
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
