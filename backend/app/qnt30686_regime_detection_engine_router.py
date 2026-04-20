from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["regime-detection-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
REGIME_DIR = ARTIFACTS_DIR / "regime_detection_engine"

DEFAULT_POLICY = {
    "minimum_regime_score": 82.0,
    "maximum_drawdown_pct": 14.0,
    "maximum_volatility_pct": 35.0,
    "maximum_concentration_pct": 45.0,
    "minimum_target_quality_score": 62.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_exception_pressure": 22.0,
    "maximum_break_pressure": 18.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"

def _path(email: str) -> Path:
    REGIME_DIR.mkdir(parents=True, exist_ok=True)
    return REGIME_DIR / f"{_safe(email)}.json"

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

def _read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback

def _latest_run(store: dict) -> dict:
    runs = store.get("runs") or []
    return runs[0] if runs else {}

def _artifact_inputs(email: str) -> dict:
    return {
        "deployment": _read_json(_artifact_file("idle_capital_deployment", email), {"policy": {}, "runs": []}),
        "reallocation": _read_json(_artifact_file("strategy_reallocation_intelligence", email), {"policy": {}, "runs": []}),
        "rotation": _read_json(_artifact_file("capital_rotation_engine", email), {"policy": {}, "runs": []}),
        "defense": _read_json(_artifact_file("drawdown_defense_system", email), {"policy": {}, "runs": []}),
        "restoration": _read_json(_artifact_file("capital_restoration_engine", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
    }

def _rows(inputs: dict, policy: dict) -> list[dict]:
    deploy_run = _latest_run(inputs["deployment"])
    realloc_run = _latest_run(inputs["reallocation"])
    rotation_run = _latest_run(inputs["rotation"])
    defense_run = _latest_run(inputs["defense"])
    restoration_run = _latest_run(inputs["restoration"])
    continuity_run = _latest_run(inputs["continuity"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    governed_capital = max(total_capital, total_mv, ledger_capital)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized

    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    exposures = [abs(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0)) for p in positions]
    volatility_pct = 0.0
    if exposures:
        avg_exp = sum(exposures) / max(len(exposures), 1)
        if avg_exp > 0:
            dispersion = sum(abs(x - avg_exp) for x in exposures) / max(len(exposures), 1)
            volatility_pct = min(100.0, (dispersion / avg_exp) * 100.0)

    alloc_values = [float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations if float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) > 0]
    concentration_pct = 0.0
    if alloc_values and governed_capital > 0:
        concentration_pct = max(alloc_values) / governed_capital * 100.0

    deployment_score = float(deploy_run.get("deployment_score") or 0.0)
    reallocation_score = float(realloc_run.get("reallocation_score") or 0.0)
    rotation_score = float(rotation_run.get("rotation_score") or 0.0)
    defense_score = float(defense_run.get("defense_score") or 0.0)
    restoration_score = float(restoration_run.get("restoration_score") or 0.0)
    continuity_score = float(continuity_run.get("continuity_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    target_quality_score = max(0.0, min(100.0,
        deployment_score * 0.20 +
        reallocation_score * 0.18 +
        rotation_score * 0.14 +
        defense_score * 0.12 +
        restoration_score * 0.10 +
        continuity_score * 0.08 +
        governance_score * 0.10 +
        compliance_score * 0.08
    ))

    exception_pressure = 0.0
    exception_pressure += float(deploy_run.get("escalate_count") or 0.0) * 5.0
    exception_pressure += float(realloc_run.get("escalate_count") or 0.0) * 4.0
    exception_pressure += float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0
    exception_pressure = min(exception_pressure, 30.0)

    break_pressure = 0.0
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        break_pressure += min(7.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.40)
    if volatility_pct > policy["maximum_volatility_pct"]:
        break_pressure += min(6.0, (volatility_pct - policy["maximum_volatility_pct"]) * 0.25)
    if concentration_pct > policy["maximum_concentration_pct"]:
        break_pressure += min(6.0, (concentration_pct - policy["maximum_concentration_pct"]) * 0.25)
    if target_quality_score < policy["minimum_target_quality_score"]:
        break_pressure += min(5.0, (policy["minimum_target_quality_score"] - target_quality_score) * 0.20)

    regime_raw = (
        deployment_score * 0.18 +
        reallocation_score * 0.16 +
        rotation_score * 0.12 +
        defense_score * 0.12 +
        restoration_score * 0.10 +
        continuity_score * 0.10 +
        governance_score * 0.12 +
        compliance_score * 0.10
    )
    regime_score = max(0.0, min(100.0, regime_raw - exception_pressure - break_pressure))

    regime_label = "NEUTRAL"
    if drawdown_pct > policy["maximum_drawdown_pct"] or volatility_pct > policy["maximum_volatility_pct"]:
        regime_label = "DEFENSIVE"
    elif target_quality_score >= policy["minimum_target_quality_score"] and concentration_pct < 35.0 and volatility_pct < 25.0:
        regime_label = "EXPANSION"
    elif concentration_pct >= 35.0:
        regime_label = "TRANSITION"

    return [{
        "portfolio_id": "REGIME_DETECTION_BOOK",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "drawdown_pct": _round_pct(drawdown_pct),
        "volatility_pct": _round_pct(volatility_pct),
        "concentration_pct": _round_pct(concentration_pct),
        "target_quality_score": _round_pct(target_quality_score),
        "deployment_score": _round_pct(deployment_score),
        "reallocation_score": _round_pct(reallocation_score),
        "rotation_score": _round_pct(rotation_score),
        "defense_score": _round_pct(defense_score),
        "restoration_score": _round_pct(restoration_score),
        "continuity_score": _round_pct(continuity_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "regime_score": _round_pct(regime_score),
        "regime_label": regime_label,
        "latest_deployment_action": deploy_run.get("deployment_posture") or deploy_run.get("action"),
        "latest_reallocation_action": realloc_run.get("reallocation_posture") or realloc_run.get("action"),
    }]

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("regime_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)
        regime_label = row.get("regime_label")
        drawdown_pct = float(row.get("drawdown_pct") or 0.0)
        volatility_pct = float(row.get("volatility_pct") or 0.0)

        action = "CLASSIFY"
        reasons = []

        if score < policy["minimum_regime_score"]:
            action = "REVIEW"
            reasons.append("regime score below threshold")
        if regime_label == "DEFENSIVE":
            action = "DEFEND"
            reasons.append("defensive regime detected")
        if regime_label == "EXPANSION" and action == "CLASSIFY":
            action = "DEPLOY"
            reasons.append("expansion regime detected")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if drawdown_pct > policy["maximum_drawdown_pct"] * 1.25 or volatility_pct > policy["maximum_volatility_pct"] * 1.2:
            action = "ESCALATE"
            reasons.append("regime instability exceeds hard threshold")
        if not reasons:
            reasons.append("regime posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "regime_score": row.get("regime_score"),
            "regime_label": row.get("regime_label"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "regime_posture": "EMPTY",
            "regime_score": 0.0,
            "classify_count": 0,
            "deploy_count": 0,
            "defend_count": 0,
            "review_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
        }
    score = sum(float(r.get("regime_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"CLASSIFY": 0, "DEPLOY": 0, "DEFEND": 0, "REVIEW": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "CLASSIFIED"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["DEFEND"] > 0:
        posture = "DEFENSIVE"
    elif counts["DEPLOY"] > 0:
        posture = "EXPANSION"
    elif counts["REVIEW"] > 0:
        posture = "UNDER_REVIEW"
    return {
        "regime_posture": posture,
        "regime_score": _round_pct(score),
        "classify_count": counts["CLASSIFY"],
        "deploy_count": counts["DEPLOY"],
        "defend_count": counts["DEFEND"],
        "review_count": counts["REVIEW"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "governed_capital_millions": _round_money(cap),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "portfolio_id": d.get("portfolio_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "regime_label": d.get("regime_label"),
            "governed_capital_millions": d.get("governed_capital_millions"),
        })
    return agenda

def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    book = _rows(inputs, policy)
    decisions = _decisions(book, policy)
    overview = _overview(book, decisions)
    return {
        "mission": "QNT30686",
        "generated_at": _now_iso(),
        "policy": policy,
        "regime_detection_overview": overview,
        "regime_book": book,
        "regime_decisions": decisions,
        "regime_dependencies": {
            "deployment_latest_run": _latest_run(inputs["deployment"]),
            "reallocation_latest_run": _latest_run(inputs["reallocation"]),
            "rotation_latest_run": _latest_run(inputs["rotation"]),
            "defense_latest_run": _latest_run(inputs["defense"]),
            "restoration_latest_run": _latest_run(inputs["restoration"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "regime_agenda": _agenda(decisions),
    }

@router.get("/api/regime-detection-engine/summary")
def regime_detection_engine_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/regime-detection-engine/run")
def regime_detection_engine_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("regime_detection_overview") or {}
    run = {
        "run_id": f"rde_{time.time_ns()}",
        "mission": "QNT30686",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "regime_posture": overview.get("regime_posture"),
        "regime_score": overview.get("regime_score"),
        "classify_count": overview.get("classify_count"),
        "deploy_count": overview.get("deploy_count"),
        "defend_count": overview.get("defend_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/regime-detection-engine/audit")
def regime_detection_engine_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30686",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/regime-detection-engine/policy")
def regime_detection_engine_policy(payload: dict = Body(...)):
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
