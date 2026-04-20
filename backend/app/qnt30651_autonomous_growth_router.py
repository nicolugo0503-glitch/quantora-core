from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["autonomous-growth-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
GROWTH_DIR = ARTIFACTS_DIR / "autonomous_growth_engine"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _crm():
    from backend.app import qnt30620_crm_router as crm
    return crm


def _pipeline():
    from backend.app import qnt30621_pipeline_router as pipeline
    return pipeline


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    GROWTH_DIR.mkdir(parents=True, exist_ok=True)
    return GROWTH_DIR / f"{_safe(email)}.json"


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
            "policy": {
                "launch_floor": 70.0,
                "channel_activation_floor": 63.0,
                "autonomy_release_floor": 76.0,
                "max_launches": 4,
                "max_sequences": 6,
            },
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


def _growth_capacity(summary: dict, crm_summary: dict, pipeline_summary: dict) -> float:
    confidence = float(summary.get("confidence_score") or 0.0)
    weighted_pipeline = float((summary.get("pipeline_overview") or {}).get("weighted_pipeline_amount") or 0.0)
    relationship_count = int(crm_summary.get("relationship_count") or 0)
    open_count = int(pipeline_summary.get("open_count") or 0)
    score = confidence * 0.58 + min(weighted_pipeline / 4000.0, 22.0) + min(relationship_count * 1.8, 10.0) + min(open_count * 2.0, 10.0)
    return _round_pct(min(max(score, 0.0), 100.0))


def _launch_queue(strategic_summary: dict, policy: dict):
    max_launches = int(policy.get("max_launches") or 4)
    launch_floor = float(policy.get("launch_floor") or 70.0)
    launches = []
    for row in strategic_summary.get("product_decisions", []) or []:
        product_score = float(row.get("product_score") or 0.0)
        if row.get("action") not in {"SCALE", "INCUBATE"}:
            continue
        if product_score < launch_floor and row.get("action") != "SCALE":
            continue
        launch_type = "product_scale" if row.get("action") == "SCALE" else "incubation_launch"
        launches.append({
            "initiative_id": f"GRW_{str(row.get('product_id') or 'PRODUCT').upper()}",
            "initiative_type": launch_type,
            "product_id": row.get("product_id"),
            "linked_strategy": row.get("linked_strategy_name") or row.get("linked_strategy_id"),
            "priority": "immediate" if product_score >= max(launch_floor + 8.0, 78.0) else "sequenced",
            "readiness_score": _round_pct(product_score),
            "target_channel": row.get("distribution_priority", "MEDIUM").lower(),
            "objective": "compound capital by converting institutional demand into recurring product AUM",
        })
    return launches[:max_launches]


def _channel_sequences(strategic_summary: dict, crm_summary: dict, pipeline_summary: dict, policy: dict):
    floor = float(policy.get("channel_activation_floor") or 63.0)
    health_counts = crm_summary.get("health_counts") or {}
    stage_counts = crm_summary.get("stage_counts") or {}
    pipeline_stages = pipeline_summary.get("stage_counts") or {}
    soft_circle = float(pipeline_stages.get("soft_commit") or 0)
    committed = float(pipeline_summary.get("committed_count") or 0)
    relationship_count = int(crm_summary.get("relationship_count") or 0)

    out = []
    for row in strategic_summary.get("distribution_priorities", []) or []:
        score = float(row.get("score") or 0.0)
        if score < floor:
            continue
        channel = row.get("channel") or "unknown"
        coverage_pressure = min(relationship_count * 1.1, 12.0) + min(float(health_counts.get("strong") or 0) * 2.0, 10.0)
        conviction = min(committed * 6.0 + soft_circle * 3.0, 18.0)
        sequence_score = min(max(score + coverage_pressure + conviction, 0.0), 100.0)
        out.append({
            "channel": channel,
            "sequence_score": _round_pct(sequence_score),
            "priority": "activate" if sequence_score >= 78.0 else "prepare",
            "next_action": "launch partner sequence" if "institutional" in channel else ("open allocator outreach sprint" if "family" in channel else "stage distribution enablement"),
            "coverage_ready_relationships": int((stage_counts.get("qualified") or 0) + (stage_counts.get("active") or 0)),
        })
    out.sort(key=lambda x: x.get("sequence_score") or 0.0, reverse=True)
    return out[: int(policy.get("max_sequences") or 6)]


def _investor_growth_sequences(crm_summary: dict, pipeline_summary: dict):
    relationships = crm_summary.get("relationships", []) or []
    opportunities = pipeline_summary.get("opportunities", []) or []
    out = []
    for rel in relationships[:4]:
        health = str(rel.get("health") or "neutral")
        stage = str(rel.get("stage") or "prospect")
        urgency = 55.0
        if health == "strong":
            urgency += 16.0
        elif health in {"watch", "at_risk"}:
            urgency += 8.0
        if stage in {"qualified", "active", "onboarding"}:
            urgency += 10.0
        linked = next((o for o in opportunities if o.get("investor_id") == rel.get("investor_id") and o.get("status") == "open"), None)
        if linked:
            urgency += min(float(linked.get("probability") or 0.0) * 0.15, 15.0)
        out.append({
            "relationship_id": rel.get("relationship_id"),
            "investor_id": rel.get("investor_id"),
            "owner": rel.get("owner") or "Unassigned",
            "sequence_type": "advance_commitment" if linked else "coverage_activation",
            "urgency_score": _round_pct(min(urgency, 100.0)),
            "next_action": rel.get("next_action") or ("schedule institutional follow-up" if linked else "open qualification sequence"),
        })
    out.sort(key=lambda x: x.get("urgency_score") or 0.0, reverse=True)
    return out


def _reinvestment_plan(strategic_summary: dict):
    capital = strategic_summary.get("capital_overview") or {}
    deployable = float(capital.get("deployable_capital") or 0.0)
    reserve = float(capital.get("cash_reserve") or 0.0)
    confidence = float(strategic_summary.get("confidence_score") or 0.0)
    growth_budget = deployable * min(max(confidence / 140.0, 0.18), 0.55)
    return {
        "deployable_capital": _round_money(deployable),
        "cash_reserve": _round_money(reserve),
        "growth_budget": _round_money(growth_budget),
        "product_launch_budget": _round_money(growth_budget * 0.38),
        "channel_activation_budget": _round_money(growth_budget * 0.27),
        "coverage_budget": _round_money(growth_budget * 0.20),
        "contingency_budget": _round_money(growth_budget * 0.15),
    }


def _constraints(strategic_summary: dict, growth_capacity: float):
    alerts = strategic_summary.get("risk_alerts") or []
    constraints = []
    for alert in alerts[:6]:
        constraints.append({
            "severity": alert.get("severity") or "warning",
            "type": alert.get("type") or "governance",
            "message": alert.get("message") or "growth constraint active",
        })
    if growth_capacity < 60.0:
        constraints.append({
            "severity": "warning",
            "type": "capacity",
            "message": "Growth capacity below autonomous release threshold; sequence only pre-authorized launches.",
        })
    return constraints


def _autonomy_posture(growth_capacity: float, strategic_summary: dict, policy: dict, constraints: list[dict]) -> str:
    posture = strategic_summary.get("operating_posture") or "defensive-observation"
    autonomy_floor = float(policy.get("autonomy_release_floor") or 76.0)
    if any(c.get("severity") == "critical" for c in constraints):
        return "governed-autonomy"
    if growth_capacity >= autonomy_floor and posture in {"scale-authorized", "measured-expansion"}:
        return "autonomous-expansion"
    if growth_capacity >= 60.0:
        return "sequenced-growth"
    return "growth-watch"


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or {}
    strategic_summary = _strategic()._build_summary(email)
    crm_summary = _crm().crm_summary()
    pipeline_summary = _pipeline().pipeline_summary()
    growth_capacity = _growth_capacity(strategic_summary, crm_summary, pipeline_summary)
    launch_queue = _launch_queue(strategic_summary, policy)
    channel_sequences = _channel_sequences(strategic_summary, crm_summary, pipeline_summary, policy)
    investor_sequences = _investor_growth_sequences(crm_summary, pipeline_summary)
    reinvestment_plan = _reinvestment_plan(strategic_summary)
    constraints = _constraints(strategic_summary, growth_capacity)
    posture = _autonomy_posture(growth_capacity, strategic_summary, policy, constraints)

    summary = {
        "mission": "QNT30651",
        "generated_at": _now_iso(),
        "autonomy_posture": posture,
        "growth_capacity_score": growth_capacity,
        "launch_queue": launch_queue,
        "channel_sequences": channel_sequences,
        "investor_sequences": investor_sequences,
        "reinvestment_plan": reinvestment_plan,
        "constraints": constraints,
        "strategic_summary": {
            "operating_posture": strategic_summary.get("operating_posture"),
            "confidence_score": strategic_summary.get("confidence_score"),
            "directive_count": len(strategic_summary.get("capital_directives") or []),
            "product_decision_count": len(strategic_summary.get("product_decisions") or []),
        },
        "crm_snapshot": {
            "relationship_count": crm_summary.get("relationship_count") or 0,
            "strong_relationships": int((crm_summary.get("health_counts") or {}).get("strong") or 0),
            "qualified_relationships": int((crm_summary.get("stage_counts") or {}).get("qualified") or 0),
            "active_relationships": int((crm_summary.get("stage_counts") or {}).get("active") or 0),
        },
        "pipeline_snapshot": {
            "open_opportunities": pipeline_summary.get("open_count") or 0,
            "committed_count": pipeline_summary.get("committed_count") or 0,
            "weighted_pipeline_amount": _round_money(pipeline_summary.get("weighted_pipeline_amount") or 0.0),
            "total_target_amount": _round_money(pipeline_summary.get("total_target_amount") or 0.0),
        },
        "execution_agenda": [
            "Convert highest-conviction product decisions into governed launch packets.",
            "Activate top distribution channels with coverage ownership and sequence controls.",
            "Route relationship follow-ups into capital raise and onboarding workflows.",
            "Reinvest approved deployable capital under reserve-aware growth budgets.",
        ],
    }
    return summary


def _log_run(email: str, summary: dict, trigger: str):
    store = _load(email)
    run = {
        "run_id": f"age_{_now_ts()}",
        "trigger": trigger,
        "timestamp": _now_iso(),
        "autonomy_posture": summary.get("autonomy_posture"),
        "growth_capacity_score": summary.get("growth_capacity_score"),
        "launch_queue": summary.get("launch_queue") or [],
        "channel_sequences": summary.get("channel_sequences") or [],
        "investor_sequences": summary.get("investor_sequences") or [],
        "reinvestment_plan": summary.get("reinvestment_plan") or {},
        "constraints": summary.get("constraints") or [],
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:100]
    _save(email, store)
    return run


@router.get("/api/autonomous-growth-engine/summary")
def autonomous_growth_engine_summary():
    session = _require_user()
    email = session.get("email")
    return _build_summary(email)


@router.post("/api/autonomous-growth-engine/run")
def autonomous_growth_engine_run(payload: dict = Body(default={})):  # noqa: B008
    session = _require_user()
    email = session.get("email")
    trigger = str(payload.get("trigger") or "manual").strip() or "manual"
    summary = _build_summary(email)
    run = _log_run(email, summary, trigger)
    return {"status": "executed", "summary": summary, "run": run}


@router.get("/api/autonomous-growth-engine/audit")
def autonomous_growth_engine_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    return {
        "mission": "QNT30651",
        "email": email,
        "run_count": len(store.get("runs", []) or []),
        "latest_run": (store.get("runs") or [None])[0],
        "runs": (store.get("runs") or [])[:25],
        "policy": store.get("policy") or {},
    }


@router.post("/api/autonomous-growth-engine/policy")
def autonomous_growth_engine_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or {}
    for key in ["launch_floor", "channel_activation_floor", "autonomy_release_floor", "max_launches", "max_sequences"]:
        if key in payload:
            policy[key] = float(payload.get(key)) if not key.startswith("max_") else int(payload.get(key))
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy}
