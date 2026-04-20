from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["institutional-closing-command"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CLOSING_DIR = ARTIFACTS_DIR / "institutional_closing_command"

DEFAULT_POLICY = {
    "priority_close_count": 8,
    "minimum_close_readiness": 78.0,
    "minimum_settlement_readiness": 74.0,
    "minimum_release_authority": 76.0,
    "maximum_execution_friction": 26.0,
    "minimum_wire_authority": 72.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _conversion():
    from backend.app import qnt30658_institutional_conversion_router as conversion
    return conversion


def _mobility():
    from backend.app import qnt30656_capital_mobility_router as mobility
    return mobility


def _treasury():
    from backend.app import qnt30655_sovereign_treasury_router as treasury
    return treasury


def _fund_close():
    from backend.app import qnt30581_fund_close_router as fund_close
    return fund_close


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    CLOSING_DIR.mkdir(parents=True, exist_ok=True)
    return CLOSING_DIR / f"{_safe(email)}.json"


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


def _close_book(dependencies: dict, policy: dict) -> list[dict]:
    conversion = dependencies["conversion"]
    mobility = dependencies["mobility"]
    treasury = dependencies["treasury"]
    closers = conversion.get("commitment_lanes") or []
    release = conversion.get("onboarding_release_matrix") or []
    transfer_queue = mobility.get("transfer_queue") or []
    reserve_matrix = mobility.get("reserve_release_matrix") or []
    settlement_grid = treasury.get("settlement_grid") or []
    count = max(int(policy.get("priority_close_count") or 8), 4)
    rows = []
    base_len = max(len(closers), 1)
    for idx in range(min(count, max(base_len, count))):
        lane = closers[idx % base_len] if closers else {}
        rel = release[idx % max(len(release), 1)] if release else {}
        transfer = transfer_queue[idx % max(len(transfer_queue), 1)] if transfer_queue else {}
        reserve = reserve_matrix[idx % max(len(reserve_matrix), 1)] if reserve_matrix else {}
        settle = settlement_grid[idx % max(len(settlement_grid), 1)] if settlement_grid else {}
        closing_prob = float(lane.get("closing_probability") or 64.0)
        doc_ready = float(lane.get("document_readiness_score") or 66.0)
        release_score = float(rel.get("release_score") or 68.0)
        mobility_score = float(transfer.get("mobility_score") or 67.0)
        wire_authority = float(reserve.get("release_score") or settle.get("settlement_readiness_score") or 69.0)
        friction = max(6.0, 44.0 - closing_prob * 0.14 - doc_ready * 0.12 - release_score * 0.08 - mobility_score * 0.06 + idx * 1.2)
        close_readiness = min(100.0, closing_prob * 0.30 + doc_ready * 0.24 + release_score * 0.20 + mobility_score * 0.16 + wire_authority * 0.10)
        rows.append({
            "close_id": f"icc_{idx+1:02d}",
            "allocator_name": lane.get("allocator_name") or f"Allocator {idx+1}",
            "vehicle": lane.get("vehicle") or settle.get("vehicle_name") or "Institutional sleeve",
            "jurisdiction": lane.get("jurisdiction") or transfer.get("source_jurisdiction") or settle.get("corridor") or "US",
            "planned_commitment_millions": _round_money(lane.get("planned_commitment_millions") or transfer.get("planned_transfer_millions") or 0.0),
            "close_readiness_score": _round_pct(close_readiness),
            "execution_friction_score": _round_pct(friction),
            "wire_authority_score": _round_pct(wire_authority),
            "status": "authorize" if close_readiness >= float(policy.get("minimum_close_readiness") or 78.0) and friction <= float(policy.get("maximum_execution_friction") or 26.0) else "prepare",
        })
    return rows


def _closing_packets(dependencies: dict, close_book: list[dict], policy: dict) -> list[dict]:
    conversion = dependencies["conversion"]
    mobility = dependencies["mobility"]
    release = conversion.get("onboarding_release_matrix") or []
    transfer_queue = mobility.get("transfer_queue") or []
    out = []
    for idx, row in enumerate(close_book):
        rel = release[idx % max(len(release), 1)] if release else {}
        transfer = transfer_queue[idx % max(len(transfer_queue), 1)] if transfer_queue else {}
        packet_score = min(100.0,
            float(row.get("close_readiness_score") or 0.0) * 0.36 +
            float(rel.get("release_score") or 68.0) * 0.22 +
            float(row.get("wire_authority_score") or 0.0) * 0.18 +
            float(transfer.get("mobility_score") or 67.0) * 0.14 +
            8.0
        )
        settlement_ready = min(100.0,
            float(row.get("wire_authority_score") or 0.0) * 0.42 +
            float(row.get("close_readiness_score") or 0.0) * 0.24 +
            float(transfer.get("mobility_score") or 67.0) * 0.18 +
            10.0
        )
        out.append({
            "packet_id": f"packet_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "vehicle": row.get("vehicle"),
            "packet_readiness_score": _round_pct(packet_score),
            "settlement_readiness_score": _round_pct(settlement_ready),
            "close_status": "release" if packet_score >= float(policy.get("minimum_release_authority") or 76.0) and settlement_ready >= float(policy.get("minimum_settlement_readiness") or 74.0) else "stage",
        })
    return out


def _settlement_matrix(dependencies: dict, close_book: list[dict], packets: list[dict], policy: dict) -> list[dict]:
    treasury = dependencies["treasury"]
    mobility = dependencies["mobility"]
    settlement_grid = treasury.get("settlement_grid") or []
    reserve_matrix = mobility.get("reserve_release_matrix") or []
    out = []
    for idx, row in enumerate(close_book):
        packet = packets[idx % max(len(packets), 1)] if packets else {}
        settle = settlement_grid[idx % max(len(settlement_grid), 1)] if settlement_grid else {}
        reserve = reserve_matrix[idx % max(len(reserve_matrix), 1)] if reserve_matrix else {}
        settlement = min(100.0,
            float(packet.get("settlement_readiness_score") or 0.0) * 0.40 +
            float(settle.get("settlement_readiness_score") or settle.get("readiness_score") or 68.0) * 0.24 +
            float(reserve.get("release_score") or 70.0) * 0.18 +
            float(row.get("wire_authority_score") or 0.0) * 0.10 +
            6.0
        )
        out.append({
            "settlement_id": f"settle_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "vehicle": row.get("vehicle"),
            "planned_commitment_millions": row.get("planned_commitment_millions") or 0.0,
            "settlement_readiness_score": _round_pct(settlement),
            "cash_route": settle.get("route") or settle.get("corridor") or reserve.get("route_name") or "governed-settlement-route",
            "settlement_status": "greenlight" if settlement >= float(policy.get("minimum_settlement_readiness") or 74.0) else "hold",
        })
    return out


def _final_release_queue(close_book: list[dict], packets: list[dict], settlement: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(close_book):
        packet = packets[idx % max(len(packets), 1)] if packets else {}
        settle = settlement[idx % max(len(settlement), 1)] if settlement else {}
        status = "launch"
        if float(row.get("wire_authority_score") or 0.0) < float(policy.get("minimum_wire_authority") or 72.0):
            status = "hold"
        if packet.get("close_status") != "release" or settle.get("settlement_status") != "greenlight":
            status = "prepare" if status != "hold" else status
        out.append({
            "release_id": f"release_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "vehicle": row.get("vehicle"),
            "next_action": "seal documents, authorize wire, and issue final close notice" if status == "launch" else ("resolve wire authority and treasury release blockers" if status == "hold" else "finish packet QA and confirm settlement lane"),
            "owner": "Institutional Closing Committee",
            "release_status": status,
        })
    return out


def _closing_overview(dependencies: dict, close_book: list[dict], packets: list[dict], settlement: list[dict], release_queue: list[dict]) -> dict:
    conversion = dependencies["conversion"]
    treasury = dependencies["treasury"]
    conversion_overview = conversion.get("conversion_overview") or {}
    treasury_overview = treasury.get("treasury_overview") or {}
    total_commitment = sum(float(x.get("planned_commitment_millions") or 0.0) for x in close_book)
    auth_count = len([x for x in close_book if x.get("status") == "authorize"])
    release_count = len([x for x in packets if x.get("close_status") == "release"])
    greenlight_count = len([x for x in settlement if x.get("settlement_status") == "greenlight"])
    launch_count = len([x for x in release_queue if x.get("release_status") == "launch"])
    avg_close = sum(float(x.get("close_readiness_score") or 0.0) for x in close_book) / max(len(close_book), 1)
    avg_settlement = sum(float(x.get("settlement_readiness_score") or 0.0) for x in settlement) / max(len(settlement), 1)
    avg_wire = sum(float(x.get("wire_authority_score") or 0.0) for x in close_book) / max(len(close_book), 1)
    avg_friction = sum(float(x.get("execution_friction_score") or 0.0) for x in close_book) / max(len(close_book), 1)
    closing_score = min(100.0,
        avg_close * 0.34 + avg_settlement * 0.24 + avg_wire * 0.18 + (100.0 - avg_friction) * 0.12 + float(conversion_overview.get("conversion_score") or 70.0) * 0.08 + float(treasury_overview.get("treasury_score") or 70.0) * 0.04
    )
    posture = "closing-command-ready"
    if launch_count < max(2, len(release_queue) // 2):
        posture = "closing-command-building"
    if avg_friction > 26.0:
        posture = "closing-command-constrained"
    return {
        "target_close_volume_millions": _round_money(total_commitment),
        "authorized_close_count": auth_count,
        "release_packet_count": release_count,
        "greenlight_settlement_count": greenlight_count,
        "launch_ready_count": launch_count,
        "average_close_readiness": _round_pct(avg_close),
        "average_settlement_readiness": _round_pct(avg_settlement),
        "average_wire_authority": _round_pct(avg_wire),
        "average_execution_friction": _round_pct(avg_friction),
        "closing_command_score": _round_pct(closing_score),
        "closing_command_posture": posture,
    }


def _closing_actions(overview: dict, release_queue: list[dict], settlement: list[dict]) -> list[str]:
    actions = []
    if overview.get("closing_command_posture") != "closing-command-ready":
        actions.append("Tighten final-close governance before scaling institutional close velocity.")
    launches = [x for x in release_queue if x.get("release_status") == "launch"][:3]
    if launches:
        actions.append("Authorize final close for " + ", ".join(x.get("allocator_name") for x in launches) + ".")
    held = [x for x in settlement if x.get("settlement_status") != "greenlight"]
    if held:
        actions.append("Resolve settlement blockers for " + ", ".join(x.get("allocator_name") for x in held[:2]) + " before wire release.")
    pending = [x for x in release_queue if x.get("release_status") == "prepare"]
    if pending:
        actions.append(f"Prepare {len(pending)} close packets for committee review and document sealing.")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    conversion = _safe_summary(_conversion()._build_summary, email, {
        "conversion_overview": {"conversion_score": 70.0, "conversion_posture": "conversion-building"},
        "commitment_lanes": [],
        "onboarding_release_matrix": [],
    })
    mobility = _safe_summary(_mobility()._build_summary, email, {
        "mobility_overview": {"mobility_score": 70.0, "mobility_posture": "governed-mobility"},
        "transfer_queue": [],
        "reserve_release_matrix": [],
    })
    treasury = _safe_summary(_treasury()._build_summary, email, {
        "treasury_overview": {"treasury_score": 70.0, "treasury_posture": "balanced"},
        "settlement_grid": [],
    })
    fund_close = _safe_summary(_fund_close().fund_close_summary, email, {})
    dependencies = {"conversion": conversion, "mobility": mobility, "treasury": treasury, "fund_close": fund_close}
    close_book = _close_book(dependencies, policy)
    packets = _closing_packets(dependencies, close_book, policy)
    settlement = _settlement_matrix(dependencies, close_book, packets, policy)
    release_queue = _final_release_queue(close_book, packets, settlement, policy)
    overview = _closing_overview(dependencies, close_book, packets, settlement, release_queue)
    return {
        "mission": "QNT30659",
        "generated_at": _now_iso(),
        "policy": policy,
        "closing_command_overview": overview,
        "close_book": close_book,
        "closing_packets": packets,
        "settlement_matrix": settlement,
        "final_release_queue": release_queue,
        "closing_dependencies": {
            "conversion_posture": (conversion.get("conversion_overview") or {}).get("conversion_posture"),
            "conversion_score": (conversion.get("conversion_overview") or {}).get("conversion_score"),
            "mobility_posture": (mobility.get("mobility_overview") or {}).get("mobility_posture"),
            "mobility_score": (mobility.get("mobility_overview") or {}).get("mobility_score"),
            "treasury_posture": (treasury.get("treasury_overview") or {}).get("treasury_posture"),
            "treasury_score": (treasury.get("treasury_overview") or {}).get("treasury_score"),
            "fund_close_summary": fund_close,
        },
        "closing_actions": _closing_actions(overview, release_queue, settlement),
    }


@router.get("/api/institutional-closing-command/summary")
def institutional_closing_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/institutional-closing-command/run")
def institutional_closing_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("closing_command_overview") or {}
    run = {
        "run_id": f"icc_{time.time_ns()}",
        "mission": "QNT30659",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "closing_command_posture": overview.get("closing_command_posture"),
        "closing_command_score": overview.get("closing_command_score"),
        "launch_ready_count": overview.get("launch_ready_count"),
        "greenlight_settlement_count": overview.get("greenlight_settlement_count"),
        "target_close_volume_millions": overview.get("target_close_volume_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/institutional-closing-command/audit")
def institutional_closing_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30659",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/institutional-closing-command/policy")
def institutional_closing_policy(payload: dict = Body(...)):
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
