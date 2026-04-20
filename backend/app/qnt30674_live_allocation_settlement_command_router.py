from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-settlement-command"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
SETTLEMENT_DIR = ARTIFACTS_DIR / "live_allocation_settlement_command"

DEFAULT_POLICY = {
    "minimum_settlement_score": 83.0,
    "maximum_settlement_stress_score": 28.0,
    "minimum_cash_coverage_pct": 88.0,
    "minimum_wire_instruction_completion_pct": 92.0,
    "minimum_broker_confirm_readiness_pct": 86.0,
    "maximum_open_exception_count": 1,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    SETTLEMENT_DIR.mkdir(parents=True, exist_ok=True)
    return SETTLEMENT_DIR / f"{_safe(email)}.json"


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
        "finalization": _read_json(_artifact_file("live_allocation_finalization_authority", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "clearance": _read_json(_artifact_file("live_allocation_clearance_grid", email), {"policy": {}, "runs": []}),
        "release": _read_json(_artifact_file("live_allocation_release_authority_mesh", email), {"policy": {}, "runs": []}),
        "dispatch": _read_json(_artifact_file("capital_dispatch_supervision_layer", email), {"policy": {}, "runs": []}),
        "treasury": _read_json(_artifact_file("sovereign_treasury_command", email), {"policy": {}, "runs": []}),
        "mobility": _read_json(_artifact_file("capital_mobility_control_plane", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "broker": _read_json(_artifact_file("broker_integration_layer", email), {"settings": {}, "positions": {}, "orders": [], "fills": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"allocations": [], "accounts": [], "entries": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "strategy_registry": [], "trades": [], "history": []}),
        "onboarding": _read_json(_artifact_file("investor_onboarding", email), {"investors": []}),
    }


def _strategy_rows(inputs: dict, policy: dict) -> list[dict]:
    finalization_run = _latest_run(inputs["finalization"])
    continuity_run = _latest_run(inputs["continuity"])
    clearance_run = _latest_run(inputs["clearance"])
    release_run = _latest_run(inputs["release"])
    dispatch_run = _latest_run(inputs["dispatch"])
    treasury_run = _latest_run(inputs["treasury"])
    mobility_run = _latest_run(inputs["mobility"])
    compliance_run = _latest_run(inputs["compliance"])
    broker_settings = inputs["broker"].get("settings") or {}
    allocations = inputs["execution"].get("strategy_allocations") or []
    accounts = inputs["ledger"].get("accounts") or []
    positions = inputs["pnl"].get("positions") or []
    onboarding = {r.get("investor_id"): r for r in (inputs["onboarding"].get("investors") or [])}
    pos_by_sleeve = {}
    for pos in positions:
        sleeve = str(pos.get("sleeve_id") or "").strip()
        if sleeve:
            pos_by_sleeve.setdefault(sleeve, []).append(pos)
    cash_available = sum(float(a.get("cash_balance") or a.get("available_cash") or 0.0) for a in accounts)
    total_alloc = sum(float(a.get("allocated_capital") or 0.0) for a in allocations) or 1.0
    base = allocations[:8] if allocations else []
    if not base:
        for idx in range(8):
            base.append({
                "strategy_id": f"STRAT_{idx+1:02d}",
                "strategy_name": f"Strategy {idx+1}",
                "allocated_capital": 0.0,
                "investor_id": None,
                "investor_name": None,
                "sleeve_id": f"sleeve_{idx+1:02d}",
            })
    base_finalization = float(finalization_run.get("finalization_score") or 82.0)
    base_continuity = float(continuity_run.get("continuity_score") or 79.0)
    base_clearance = float(clearance_run.get("clearance_score") or clearance_run.get("average_clearance_score") or 84.0)
    base_release = float(release_run.get("release_score") or release_run.get("average_release_score") or 82.0)
    base_dispatch = float(dispatch_run.get("dispatch_score") or dispatch_run.get("average_dispatch_score") or 81.0)
    base_treasury = float(treasury_run.get("treasury_score") or 80.0)
    base_mobility = float(mobility_run.get("mobility_score") or mobility_run.get("average_mobility_score") or 79.0)
    base_stress = float(treasury_run.get("average_settlement_stress") or 22.0)
    compliance_pressure = float(compliance_run.get("release_score") or compliance_run.get("average_release_score") or 86.0)
    live_mode_bonus = 8.0 if str(broker_settings.get("mode") or "").lower() == "live" else -6.0
    live_permission_bonus = 10.0 if broker_settings.get("allow_live_execution") else -15.0
    rows = []
    for idx, alloc in enumerate(base):
        sleeve = str(alloc.get("sleeve_id") or alloc.get("strategy_id") or f"sleeve_{idx+1:02d}")
        strategy_positions = pos_by_sleeve.get(sleeve, [])
        allocated_capital = float(alloc.get("allocated_capital") or 0.0)
        gross_pnl = sum(float(p.get("realized_pnl") or 0.0) + float(p.get("unrealized_pnl") or 0.0) for p in strategy_positions)
        required_cash = max(allocated_capital * 0.06, 25000.0)
        cash_coverage_pct = min(100.0, (cash_available / max(required_cash, 1.0)) * 100.0)
        checklist = (onboarding.get(alloc.get("investor_id")) or {}).get("checklist") or {}
        if checklist:
            wire_instruction_completion_pct = sum(1 for v in checklist.values() if v) / max(len(checklist), 1) * 100.0
        else:
            wire_instruction_completion_pct = max(88.0, 97.0 - idx * 1.4)
        broker_confirm_readiness_pct = min(100.0,
            58.0
            + base_release * 0.10
            + base_dispatch * 0.11
            + base_treasury * 0.08
            + base_mobility * 0.07
            + live_mode_bonus
            + live_permission_bonus
            - idx * 1.25
        )
        settlement_stress_score = max(0.0,
            base_stress
            + idx * 1.1
            + max(0.0, 70.0 - cash_coverage_pct) * 0.18
            + max(0.0, 90.0 - broker_confirm_readiness_pct) * 0.10
            + max(0.0, 90.0 - wire_instruction_completion_pct) * 0.06
        )
        open_exception_count = 0
        if cash_coverage_pct < float(policy.get("minimum_cash_coverage_pct") or 88.0):
            open_exception_count += 1
        if wire_instruction_completion_pct < float(policy.get("minimum_wire_instruction_completion_pct") or 92.0):
            open_exception_count += 1
        if broker_confirm_readiness_pct < float(policy.get("minimum_broker_confirm_readiness_pct") or 86.0):
            open_exception_count += 1
        if settlement_stress_score > float(policy.get("maximum_settlement_stress_score") or 28.0):
            open_exception_count += 1
        settlement_score = min(100.0,
            base_finalization * 0.24
            + base_continuity * 0.18
            + base_clearance * 0.12
            + base_release * 0.10
            + base_dispatch * 0.10
            + base_treasury * 0.10
            + base_mobility * 0.08
            + compliance_pressure * 0.08
            + cash_coverage_pct * 0.10
            + wire_instruction_completion_pct * 0.05
            + broker_confirm_readiness_pct * 0.05
            - settlement_stress_score * 0.65
            - idx * 1.35
        )
        route = f"{(alloc.get('investor_name') or alloc.get('strategy_id') or 'allocator').replace(' ', '-').lower()}-settlement-lane"
        rows.append({
            "settlement_case_id": f"lasc_{idx+1:02d}",
            "strategy_id": str(alloc.get("strategy_id") or f"STRAT_{idx+1:02d}"),
            "strategy_name": alloc.get("strategy_name") or f"Strategy {idx+1}",
            "allocator_name": alloc.get("investor_name") or alloc.get("investor_id") or f"Allocator {idx+1}",
            "invested_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "gross_pnl_millions": _round_money(gross_pnl / 1_000_000.0),
            "concentration_pct": _round_pct(allocated_capital / total_alloc * 100.0 if total_alloc else 0.0),
            "cash_coverage_pct": _round_pct(cash_coverage_pct),
            "wire_instruction_completion_pct": _round_pct(wire_instruction_completion_pct),
            "broker_confirm_readiness_pct": _round_pct(broker_confirm_readiness_pct),
            "settlement_stress_score": _round_pct(settlement_stress_score),
            "settlement_window_days": 1 + (idx % 4),
            "settlement_route": route,
            "open_exception_count": int(open_exception_count),
            "settlement_score": _round_pct(settlement_score),
        })
    return rows


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    out = []
    for row in rows:
        reasons = []
        if float(row.get("cash_coverage_pct") or 0.0) < float(policy.get("minimum_cash_coverage_pct") or 88.0):
            reasons.append("CASH_COVERAGE_GAP")
        if float(row.get("wire_instruction_completion_pct") or 0.0) < float(policy.get("minimum_wire_instruction_completion_pct") or 92.0):
            reasons.append("WIRE_INSTRUCTION_GAP")
        if float(row.get("broker_confirm_readiness_pct") or 0.0) < float(policy.get("minimum_broker_confirm_readiness_pct") or 86.0):
            reasons.append("BROKER_CONFIRM_GAP")
        if float(row.get("settlement_stress_score") or 0.0) > float(policy.get("maximum_settlement_stress_score") or 28.0):
            reasons.append("SETTLEMENT_STRESS")
        if int(row.get("open_exception_count") or 0) > int(policy.get("maximum_open_exception_count") or 1):
            reasons.append("EXCEPTION_OVERFLOW")
        score = float(row.get("settlement_score") or 0.0)
        if reasons and score < float(policy.get("minimum_settlement_score") or 83.0) - 8.0:
            action = "ESCALATE"
        elif reasons:
            action = "HOLD"
        elif score >= float(policy.get("minimum_settlement_score") or 83.0) + 4.0:
            action = "SETTLE"
        else:
            action = "REVIEW"
        out.append({
            "settlement_case_id": row.get("settlement_case_id"),
            "strategy_id": row.get("strategy_id"),
            "action": action,
            "priority": "HIGH" if action in {"ESCALATE", "HOLD"} else ("MEDIUM" if action == "REVIEW" else "NORMAL"),
            "reasons": reasons or ["IN_POLICY"],
            "next_action": {
                "SETTLE": "Authorize wire release and confirm broker-side settlement completion.",
                "REVIEW": "Review settlement packet and treasury lane before release.",
                "HOLD": "Hold settlement until readiness gaps and stress factors are remediated.",
                "ESCALATE": "Escalate to treasury, compliance, and operations committee for supervised intervention.",
            }[action],
        })
    return out


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    avg_score = sum(float(r.get("settlement_score") or 0.0) for r in rows) / max(len(rows), 1)
    avg_stress = sum(float(r.get("settlement_stress_score") or 0.0) for r in rows) / max(len(rows), 1)
    total_capital = sum(float(r.get("invested_capital_millions") or 0.0) for r in rows)
    settle_count = len([d for d in decisions if d.get("action") == "SETTLE"])
    review_count = len([d for d in decisions if d.get("action") == "REVIEW"])
    hold_count = len([d for d in decisions if d.get("action") == "HOLD"])
    escalate_count = len([d for d in decisions if d.get("action") == "ESCALATE"])
    posture = "greenlight"
    if escalate_count:
        posture = "escalated"
    elif hold_count:
        posture = "constrained"
    elif review_count:
        posture = "review"
    return {
        "settlement_score": _round_pct(avg_score),
        "settlement_posture": posture,
        "settlement_capital_millions": _round_money(total_capital),
        "average_settlement_stress_score": _round_pct(avg_stress),
        "settle_count": settle_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "escalate_count": escalate_count,
    }


def _agenda(decisions: list[dict]) -> list[str]:
    agenda = []
    for action_name, text in [
        ("ESCALATE", "Escalate settlement intervention for"),
        ("HOLD", "Hold settlement release for"),
        ("REVIEW", "Review settlement packet for"),
        ("SETTLE", "Authorize live settlement for"),
    ]:
        items = [d for d in decisions if d.get("action") == action_name][:3]
        if items:
            agenda.append(f"{text} {', '.join(i.get('strategy_id') for i in items)}.")
    if not agenda:
        agenda.append("No settlement actions required.")
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    settlement_book = _strategy_rows(inputs, policy)
    settlement_decisions = _decisions(settlement_book, policy)
    overview = _overview(settlement_book, settlement_decisions)
    return {
        "mission": "QNT30674",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_settlement_overview": overview,
        "settlement_book": settlement_book,
        "settlement_decisions": settlement_decisions,
        "settlement_dependencies": {
            "finalization_latest_run": _latest_run(inputs["finalization"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "clearance_latest_run": _latest_run(inputs["clearance"]),
            "release_latest_run": _latest_run(inputs["release"]),
            "dispatch_latest_run": _latest_run(inputs["dispatch"]),
            "treasury_latest_run": _latest_run(inputs["treasury"]),
            "mobility_latest_run": _latest_run(inputs["mobility"]),
            "broker_settings": inputs["broker"].get("settings") or {},
        },
        "settlement_agenda": _agenda(settlement_decisions),
    }


@router.get("/api/live-allocation-settlement-command/summary")
def live_allocation_settlement_command_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-settlement-command/run")
def live_allocation_settlement_command_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_settlement_overview") or {}
    run = {
        "run_id": f"lasc_{time.time_ns()}",
        "mission": "QNT30674",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "settlement_posture": overview.get("settlement_posture"),
        "settlement_score": overview.get("settlement_score"),
        "settle_count": overview.get("settle_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "settlement_capital_millions": overview.get("settlement_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-settlement-command/audit")
def live_allocation_settlement_command_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30674",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-settlement-command/policy")
def live_allocation_settlement_command_policy(payload: dict = Body(...)):
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
