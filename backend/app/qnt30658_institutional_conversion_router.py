from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["institutional-conversion-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CONVERSION_DIR = ARTIFACTS_DIR / "institutional_conversion_engine"

DEFAULT_POLICY = {
    "priority_conversion_count": 8,
    "minimum_commitment_readiness": 74.0,
    "minimum_closing_probability": 67.0,
    "minimum_subscription_completeness": 72.0,
    "minimum_conversion_score": 76.0,
    "maximum_friction_score": 30.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _allocator():
    from backend.app import qnt30657_allocator_command_router as allocator
    return allocator


def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as compliance
    return compliance


def _funds():
    from backend.app import qnt30653_multi_fund_architecture_router as funds
    return funds


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    CONVERSION_DIR.mkdir(parents=True, exist_ok=True)
    return CONVERSION_DIR / f"{_safe(email)}.json"


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


def _safe_summary(builder, email: str, fallback: dict):
    try:
        return builder(email)
    except Exception:
        return dict(fallback)


def _conversion_book(dependencies: dict, policy: dict) -> list[dict]:
    allocator = dependencies["allocator"]
    compliance = dependencies["compliance"]
    funds = dependencies["funds"]
    allocator_book = allocator.get("allocator_book") or []
    command_routes = allocator.get("command_routes") or []
    coverage_matrix = allocator.get("coverage_matrix") or []
    compliance_matrix = compliance.get("jurisdiction_matrix") or []
    vehicles = funds.get("vehicle_stack") or []
    count = max(int(policy.get("priority_conversion_count") or 8), 4)
    rows = []
    for idx in range(min(count, max(len(allocator_book), count))):
        book = allocator_book[idx % max(len(allocator_book), 1)] if allocator_book else {}
        route = command_routes[idx % max(len(command_routes), 1)] if command_routes else {}
        coverage = coverage_matrix[idx % max(len(coverage_matrix), 1)] if coverage_matrix else {}
        compliance_row = compliance_matrix[idx % max(len(compliance_matrix), 1)] if compliance_matrix else {}
        vehicle = vehicles[idx % max(len(vehicles), 1)] if vehicles else {}
        conviction = float(book.get("allocator_conviction_score") or 64.0)
        command = float(route.get("command_score") or 62.0)
        cov = float(coverage.get("coverage_score") or 60.0)
        gap = float(coverage.get("relationship_gap_score") or 35.0)
        compliance_score = float(compliance_row.get("readiness_score") or compliance_row.get("jurisdiction_readiness_score") or 68.0)
        subscription = min(100.0, conviction * 0.18 + command * 0.24 + cov * 0.18 + compliance_score * 0.22 + 8.0)
        commitment = min(100.0, conviction * 0.24 + command * 0.24 + cov * 0.18 + compliance_score * 0.2 + (100.0 - gap) * 0.1 + 6.0)
        friction = max(8.0, 48.0 - command * 0.16 - cov * 0.12 - compliance_score * 0.1 + idx * 1.7)
        target_commitment = float(book.get("expected_ticket_millions") or route.get("planned_ticket_millions") or 2.0) * (1.05 + idx * 0.035)
        rows.append({
            "conversion_id": f"ice_{idx+1:02d}",
            "allocator_name": book.get("allocator_name") or f"Allocator {idx+1}",
            "segment": book.get("segment") or "institutional_allocator",
            "vehicle": vehicle.get("vehicle_name") or vehicle.get("vehicle_id") or "Flagship feeder sleeve",
            "jurisdiction": compliance_row.get("jurisdiction") or compliance_row.get("region") or book.get("coverage_region") or "US",
            "target_commitment_millions": _round_money(target_commitment),
            "commitment_readiness_score": _round_pct(commitment),
            "subscription_completeness_score": _round_pct(subscription),
            "friction_score": _round_pct(friction),
            "status": "advance" if commitment >= float(policy.get("minimum_commitment_readiness") or 74.0) and friction <= float(policy.get("maximum_friction_score") or 30.0) else "prepare",
        })
    return rows


def _commitment_lanes(dependencies: dict, conversion_book: list[dict], policy: dict) -> list[dict]:
    allocator = dependencies["allocator"]
    compliance = dependencies["compliance"]
    funds = dependencies["funds"]
    routes = allocator.get("command_routes") or []
    compliance_matrix = compliance.get("jurisdiction_matrix") or []
    fund_matrix = funds.get("fund_matrix") or []
    out = []
    for idx, row in enumerate(conversion_book):
        route = routes[idx % max(len(routes), 1)] if routes else {}
        compliance_row = compliance_matrix[idx % max(len(compliance_matrix), 1)] if compliance_matrix else {}
        fund_row = fund_matrix[idx % max(len(fund_matrix), 1)] if fund_matrix else {}
        closing_probability = min(100.0,
            float(row.get("commitment_readiness_score") or 0.0) * 0.38 +
            float(row.get("subscription_completeness_score") or 0.0) * 0.26 +
            float(compliance_row.get("readiness_score") or compliance_row.get("jurisdiction_readiness_score") or 68.0) * 0.18 +
            float(route.get("ticket_capture_ratio") or 56.0) * 0.1 +
            6.0
        )
        docs_ready = min(100.0,
            float(row.get("subscription_completeness_score") or 0.0) * 0.62 +
            float(compliance_row.get("readiness_score") or compliance_row.get("jurisdiction_readiness_score") or 68.0) * 0.18 +
            10.0
        )
        out.append({
            "lane_id": f"lane_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "vehicle": row.get("vehicle"),
            "jurisdiction": row.get("jurisdiction"),
            "fund_route": fund_row.get("fund_name") or fund_row.get("domicile") or row.get("vehicle"),
            "planned_commitment_millions": row.get("target_commitment_millions") or 0.0,
            "closing_probability": _round_pct(closing_probability),
            "document_readiness_score": _round_pct(docs_ready),
            "status": "close" if closing_probability >= float(policy.get("minimum_closing_probability") or 67.0) and docs_ready >= float(policy.get("minimum_subscription_completeness") or 72.0) else "stage",
        })
    return out


def _closing_queue(commitment_lanes: list[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(commitment_lanes):
        status = row.get("status")
        out.append({
            "queue_id": f"close_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "vehicle": row.get("vehicle"),
            "planned_commitment_millions": row.get("planned_commitment_millions") or 0.0,
            "next_action": "issue subscription packet and book closing call" if status == "close" else "finish diligence package and resolve blockers",
            "owner": "Institutional Conversion Desk",
            "status": "launch" if status == "close" else "prepare",
        })
    return out


def _onboarding_release_matrix(dependencies: dict, commitment_lanes: list[dict], conversion_book: list[dict], policy: dict) -> list[dict]:
    compliance = dependencies["compliance"]
    compliance_matrix = compliance.get("jurisdiction_matrix") or []
    out = []
    for idx, row in enumerate(commitment_lanes):
        base = conversion_book[idx % max(len(conversion_book), 1)] if conversion_book else {}
        compliance_row = compliance_matrix[idx % max(len(compliance_matrix), 1)] if compliance_matrix else {}
        release_score = min(100.0,
            float(row.get("document_readiness_score") or 0.0) * 0.42 +
            float(row.get("closing_probability") or 0.0) * 0.28 +
            float(compliance_row.get("readiness_score") or compliance_row.get("jurisdiction_readiness_score") or 68.0) * 0.18 +
            8.0
        )
        out.append({
            "release_id": f"rel_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "vehicle": row.get("vehicle"),
            "subscription_completeness_score": base.get("subscription_completeness_score") or 0.0,
            "release_score": _round_pct(release_score),
            "release_status": "release" if release_score >= float(policy.get("minimum_conversion_score") or 76.0) else "hold",
        })
    return out


def _conversion_overview(dependencies: dict, conversion_book: list[dict], commitment_lanes: list[dict], closing_queue: list[dict], release_matrix: list[dict]) -> dict:
    allocator = dependencies["allocator"]
    overview = allocator.get("allocator_command_overview") or {}
    total_commitment = sum(float(x.get("target_commitment_millions") or 0.0) for x in conversion_book)
    advanced = [x for x in conversion_book if x.get("status") == "advance"]
    closers = [x for x in commitment_lanes if x.get("status") == "close"]
    launched = [x for x in closing_queue if x.get("status") == "launch"]
    releasable = [x for x in release_matrix if x.get("release_status") == "release"]
    avg_commitment = sum(float(x.get("commitment_readiness_score") or 0.0) for x in conversion_book) / max(len(conversion_book), 1)
    avg_probability = sum(float(x.get("closing_probability") or 0.0) for x in commitment_lanes) / max(len(commitment_lanes), 1)
    avg_release = sum(float(x.get("release_score") or 0.0) for x in release_matrix) / max(len(release_matrix), 1)
    avg_friction = sum(float(x.get("friction_score") or 0.0) for x in conversion_book) / max(len(conversion_book), 1)
    conversion_score = min(100.0,
        avg_commitment * 0.34 + avg_probability * 0.28 + avg_release * 0.22 + (100.0 - avg_friction) * 0.1 + float(overview.get("command_network_score") or 68.0) * 0.06
    )
    posture = "conversion-primed"
    if len(closers) < max(2, len(commitment_lanes) // 2):
        posture = "conversion-building"
    if avg_friction > 30.0:
        posture = "conversion-constrained"
    return {
        "allocator_ticket_pipeline_millions": _round_money(float(overview.get("allocator_ticket_pipeline_millions") or 0.0)),
        "target_commitment_pipeline_millions": _round_money(total_commitment),
        "advanced_allocator_count": len(advanced),
        "closing_ready_count": len(closers),
        "launch_ready_count": len(launched),
        "release_ready_count": len(releasable),
        "average_commitment_readiness": _round_pct(avg_commitment),
        "average_closing_probability": _round_pct(avg_probability),
        "average_release_score": _round_pct(avg_release),
        "average_friction_score": _round_pct(avg_friction),
        "conversion_score": _round_pct(conversion_score),
        "conversion_posture": posture,
    }


def _conversion_actions(overview: dict, commitment_lanes: list[dict], closing_queue: list[dict], release_matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("conversion_posture") != "conversion-primed":
        actions.append("Tighten subscription readiness and resolve diligence friction before opening full institutional closing velocity.")
    closers = [x for x in commitment_lanes if x.get("status") == "close"][:3]
    if closers:
        actions.append("Prioritize closing committee motions for " + ", ".join(x.get("allocator_name") for x in closers) + ".")
    pending = [x for x in closing_queue if x.get("status") != "launch"]
    if pending:
        actions.append(f"Prepare {len(pending)} staged allocator lanes with updated data-room evidence and subscription packets.")
    held = [x for x in release_matrix if x.get("release_status") != "release"]
    if held:
        actions.append("Hold release for " + ", ".join(x.get("allocator_name") for x in held[:2]) + " until compliance and subscription completeness cross release thresholds.")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    allocator = _safe_summary(_allocator()._build_summary, email, {
        "allocator_command_overview": {"command_network_score": 68.0, "allocator_ticket_pipeline_millions": 0.0},
        "allocator_book": [],
        "command_routes": [],
        "coverage_matrix": [],
    })
    compliance = _safe_summary(_compliance()._build_summary, email, {
        "compliance_overview": {"supervisory_release_score": 70.0},
        "jurisdiction_matrix": [],
    })
    funds = _safe_summary(_funds()._build_summary, email, {
        "architecture_overview": {"multi_fund_score": 70.0},
        "vehicle_stack": [],
        "fund_matrix": [],
    })
    dependencies = {"allocator": allocator, "compliance": compliance, "funds": funds}
    conversion_book = _conversion_book(dependencies, policy)
    commitment_lanes = _commitment_lanes(dependencies, conversion_book, policy)
    closing_queue = _closing_queue(commitment_lanes)
    release_matrix = _onboarding_release_matrix(dependencies, commitment_lanes, conversion_book, policy)
    overview = _conversion_overview(dependencies, conversion_book, commitment_lanes, closing_queue, release_matrix)
    return {
        "mission": "QNT30658",
        "generated_at": _now_iso(),
        "policy": policy,
        "conversion_overview": overview,
        "allocator_conversion_book": conversion_book,
        "commitment_lanes": commitment_lanes,
        "closing_queue": closing_queue,
        "onboarding_release_matrix": release_matrix,
        "conversion_dependencies": {
            "allocator_command_posture": (allocator.get("allocator_command_overview") or {}).get("allocator_command_posture"),
            "command_network_score": (allocator.get("allocator_command_overview") or {}).get("command_network_score"),
            "compliance_posture": (compliance.get("compliance_overview") or {}).get("compliance_posture"),
            "supervisory_release_score": (compliance.get("compliance_overview") or {}).get("supervisory_release_score"),
            "multi_fund_posture": (funds.get("architecture_overview") or {}).get("architecture_posture"),
            "multi_fund_score": (funds.get("architecture_overview") or {}).get("multi_fund_score"),
        },
        "conversion_actions": _conversion_actions(overview, commitment_lanes, closing_queue, release_matrix),
    }


@router.get("/api/institutional-conversion-engine/summary")
def institutional_conversion_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/institutional-conversion-engine/run")
def institutional_conversion_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("conversion_overview") or {}
    run = {
        "run_id": f"ice_{time.time_ns()}",
        "mission": "QNT30658",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "conversion_posture": overview.get("conversion_posture"),
        "conversion_score": overview.get("conversion_score"),
        "closing_ready_count": overview.get("closing_ready_count"),
        "release_ready_count": overview.get("release_ready_count"),
        "target_commitment_pipeline_millions": overview.get("target_commitment_pipeline_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/institutional-conversion-engine/audit")
def institutional_conversion_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30658",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/institutional-conversion-engine/policy")
def institutional_conversion_policy(payload: dict = Body(...)):
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
