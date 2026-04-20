from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-reconciliation-command"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
RECON_DIR = ARTIFACTS_DIR / "live_allocation_reconciliation_command"

DEFAULT_POLICY = {
    "minimum_reconciliation_score": 84.0,
    "minimum_ledger_alignment_pct": 90.0,
    "minimum_fill_capture_pct": 88.0,
    "minimum_position_match_pct": 86.0,
    "maximum_reconciliation_stress_score": 26.0,
    "maximum_break_count": 1,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    RECON_DIR.mkdir(parents=True, exist_ok=True)
    return RECON_DIR / f"{_safe(email)}.json"


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
        "settlement": _read_json(_artifact_file("live_allocation_settlement_command", email), {"policy": {}, "runs": []}),
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


def _sum_amounts(items, keys):
    total = 0.0
    for item in items:
        for key in keys:
            if key in item and item.get(key) is not None:
                try:
                    total += abs(float(item.get(key) or 0.0))
                    break
                except Exception:
                    pass
    return total


def _strategy_rows(inputs: dict, policy: dict) -> list[dict]:
    settlement_run = _latest_run(inputs["settlement"])
    finalization_run = _latest_run(inputs["finalization"])
    continuity_run = _latest_run(inputs["continuity"])
    clearance_run = _latest_run(inputs["clearance"])
    release_run = _latest_run(inputs["release"])
    dispatch_run = _latest_run(inputs["dispatch"])
    treasury_run = _latest_run(inputs["treasury"])
    mobility_run = _latest_run(inputs["mobility"])
    compliance_run = _latest_run(inputs["compliance"])
    broker = inputs["broker"]
    allocations = inputs["execution"].get("strategy_allocations") or []
    accounts = inputs["ledger"].get("accounts") or []
    entries = inputs["ledger"].get("entries") or []
    positions = inputs["pnl"].get("positions") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    trades = inputs["execution"].get("trades") or []
    history = inputs["execution"].get("history") or []
    fills = broker.get("fills") or []
    orders = broker.get("orders") or []
    onboarding = {r.get("investor_id"): r for r in (inputs["onboarding"].get("investors") or [])}

    pos_by_sleeve = {}
    for pos in positions:
        sleeve = str(pos.get("sleeve_id") or "").strip()
        if sleeve:
            pos_by_sleeve.setdefault(sleeve, []).append(pos)

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

    total_alloc = sum(float(a.get("allocated_capital") or 0.0) for a in base) or 1.0
    total_cash = sum(float(a.get("cash_balance") or a.get("available_cash") or 0.0) for a in accounts)
    base_settlement = float(settlement_run.get("settlement_score") or 82.0)
    base_finalization = float(finalization_run.get("finalization_score") or 81.0)
    base_continuity = float(continuity_run.get("continuity_score") or 79.0)
    base_clearance = float(clearance_run.get("clearance_score") or 83.0)
    base_release = float(release_run.get("release_score") or 82.0)
    base_dispatch = float(dispatch_run.get("dispatch_score") or 81.0)
    base_treasury = float(treasury_run.get("treasury_score") or 80.0)
    base_mobility = float(mobility_run.get("mobility_score") or 79.0)
    compliance_release = float(compliance_run.get("release_score") or 86.0)
    broker_live_bonus = 7.0 if str((broker.get("settings") or {}).get("mode") or "").lower() == "live" else -4.0

    rows = []
    for idx, alloc in enumerate(base):
        strategy_id = str(alloc.get("strategy_id") or f"STRAT_{idx+1:02d}")
        sleeve = str(alloc.get("sleeve_id") or strategy_id)
        investor_id = alloc.get("investor_id")
        investor_name = alloc.get("investor_name") or investor_id or f"Allocator {idx+1}"

        strategy_positions = pos_by_sleeve.get(sleeve, [])
        strategy_entries = [e for e in entries if str(e.get("sleeve_id") or e.get("strategy_id") or "") in {sleeve, strategy_id}]
        strategy_pnl_entries = [e for e in pnl_ledger if str(e.get("sleeve_id") or e.get("strategy_id") or "") in {sleeve, strategy_id}]
        strategy_trades = [t for t in trades if str(t.get("sleeve_id") or t.get("strategy_id") or "") in {sleeve, strategy_id}]
        strategy_history = [t for t in history if str(t.get("sleeve_id") or t.get("strategy_id") or "") in {sleeve, strategy_id}]
        strategy_orders = [o for o in orders if str(o.get("sleeve_id") or o.get("strategy_id") or "") in {sleeve, strategy_id}]
        strategy_fills = [f for f in fills if str(f.get("sleeve_id") or f.get("strategy_id") or "") in {sleeve, strategy_id}]

        allocated_capital = float(alloc.get("allocated_capital") or 0.0)
        ledger_notional = _sum_amounts(strategy_entries, ["amount", "capital_amount", "net_cash_flow", "cash_flow"])
        pnl_notional = _sum_amounts(strategy_pnl_entries, ["amount", "pnl_amount", "realized_pnl", "unrealized_pnl"])
        executed_notional = _sum_amounts(strategy_trades + strategy_history, ["notional", "filled_notional", "gross_notional", "amount"]) or max(allocated_capital * 0.92, 1.0)
        fill_notional = _sum_amounts(strategy_fills, ["filled_notional", "notional", "amount"])
        if fill_notional <= 0 and strategy_orders:
            fill_notional = _sum_amounts(strategy_orders, ["notional", "filled_notional", "amount"]) * 0.88

        ledger_anchor = max(executed_notional, ledger_notional, allocated_capital * 0.5, 1.0)
        pnl_anchor = max(abs(pnl_notional), sum(abs(float(p.get("realized_pnl") or 0.0) + float(p.get("unrealized_pnl") or 0.0)) for p in strategy_positions), 1.0)

        ledger_alignment_pct = max(0.0, 100.0 - abs(executed_notional - ledger_notional) / ledger_anchor * 100.0)
        fill_capture_pct = min(100.0, (fill_notional / max(executed_notional, 1.0)) * 100.0)
        position_match_pct = min(100.0, 62.0 + len(strategy_positions) * 9.0 + min(20.0, pnl_anchor / max(allocated_capital, 1.0) * 100.0))
        if strategy_positions:
            broker_position_match_bonus = 6.0
        else:
            broker_position_match_bonus = -3.0
        position_match_pct = max(0.0, min(100.0, position_match_pct + broker_position_match_bonus))

        documented_checklist = (onboarding.get(investor_id) or {}).get("checklist") or {}
        documentation_completion_pct = (sum(1 for v in documented_checklist.values() if v) / max(len(documented_checklist), 1) * 100.0) if documented_checklist else max(87.0, 96.0 - idx * 1.2)

        reconciliation_break_count = 0
        if ledger_alignment_pct < float(policy.get("minimum_ledger_alignment_pct") or 90.0):
            reconciliation_break_count += 1
        if fill_capture_pct < float(policy.get("minimum_fill_capture_pct") or 88.0):
            reconciliation_break_count += 1
        if position_match_pct < float(policy.get("minimum_position_match_pct") or 86.0):
            reconciliation_break_count += 1
        if documentation_completion_pct < 90.0:
            reconciliation_break_count += 1

        reconciliation_stress_score = max(0.0,
            (100.0 - ledger_alignment_pct) * 0.28
            + (100.0 - fill_capture_pct) * 0.22
            + (100.0 - position_match_pct) * 0.18
            + reconciliation_break_count * 4.5
            + idx * 0.9
            + max(0.0, 60.0 - min(100.0, total_cash / max(allocated_capital * 0.05, 1.0) * 100.0)) * 0.06
        )

        reconciliation_score = min(100.0,
            base_settlement * 0.18
            + base_finalization * 0.12
            + base_continuity * 0.10
            + base_clearance * 0.08
            + base_release * 0.08
            + base_dispatch * 0.08
            + base_treasury * 0.07
            + base_mobility * 0.06
            + compliance_release * 0.08
            + ledger_alignment_pct * 0.12
            + fill_capture_pct * 0.10
            + position_match_pct * 0.10
            + documentation_completion_pct * 0.05
            + broker_live_bonus
            - reconciliation_stress_score * 0.65
            - idx * 1.15
        )

        gross_pnl = sum(float(p.get("realized_pnl") or 0.0) + float(p.get("unrealized_pnl") or 0.0) for p in strategy_positions)
        rows.append({
            "reconciliation_case_id": f"larc_{idx+1:02d}",
            "strategy_id": strategy_id,
            "strategy_name": alloc.get("strategy_name") or f"Strategy {idx+1}",
            "allocator_name": investor_name,
            "invested_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "gross_pnl_millions": _round_money(gross_pnl / 1_000_000.0),
            "concentration_pct": _round_pct(allocated_capital / total_alloc * 100.0 if total_alloc else 0.0),
            "ledger_alignment_pct": _round_pct(ledger_alignment_pct),
            "fill_capture_pct": _round_pct(fill_capture_pct),
            "position_match_pct": _round_pct(position_match_pct),
            "documentation_completion_pct": _round_pct(documentation_completion_pct),
            "reconciliation_break_count": int(reconciliation_break_count),
            "reconciliation_stress_score": _round_pct(reconciliation_stress_score),
            "trade_count": len(strategy_trades) + len(strategy_history),
            "fill_count": len(strategy_fills),
            "ledger_entry_count": len(strategy_entries),
            "reconciliation_score": _round_pct(reconciliation_score),
        })
    return rows


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    out = []
    for row in rows:
        reasons = []
        if float(row.get("ledger_alignment_pct") or 0.0) < float(policy.get("minimum_ledger_alignment_pct") or 90.0):
            reasons.append("LEDGER_ALIGNMENT_GAP")
        if float(row.get("fill_capture_pct") or 0.0) < float(policy.get("minimum_fill_capture_pct") or 88.0):
            reasons.append("FILL_CAPTURE_GAP")
        if float(row.get("position_match_pct") or 0.0) < float(policy.get("minimum_position_match_pct") or 86.0):
            reasons.append("POSITION_MATCH_GAP")
        if float(row.get("reconciliation_stress_score") or 0.0) > float(policy.get("maximum_reconciliation_stress_score") or 26.0):
            reasons.append("RECONCILIATION_STRESS")
        if int(row.get("reconciliation_break_count") or 0) > int(policy.get("maximum_break_count") or 1):
            reasons.append("BREAK_OVERFLOW")
        score = float(row.get("reconciliation_score") or 0.0)
        if reasons and score < float(policy.get("minimum_reconciliation_score") or 84.0) - 9.0:
            action = "ESCALATE"
        elif reasons:
            action = "HOLD"
        elif score >= float(policy.get("minimum_reconciliation_score") or 84.0) + 4.0:
            action = "RECONCILE"
        else:
            action = "REVIEW"
        out.append({
            "reconciliation_case_id": row.get("reconciliation_case_id"),
            "strategy_id": row.get("strategy_id"),
            "action": action,
            "priority": "HIGH" if action in {"ESCALATE", "HOLD"} else ("MEDIUM" if action == "REVIEW" else "NORMAL"),
            "reasons": reasons or ["IN_POLICY"],
            "next_action": {
                "RECONCILE": "Finalize reconciliation pack and release matched accounting records.",
                "REVIEW": "Review reconciliation breaks and validate supporting broker or ledger artifacts.",
                "HOLD": "Hold allocation accounting close until breaks are remediated.",
                "ESCALATE": "Escalate reconciliation exceptions to operations, treasury, and governance control.",
            }[action],
        })
    return out


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    avg_score = sum(float(r.get("reconciliation_score") or 0.0) for r in rows) / max(len(rows), 1)
    avg_stress = sum(float(r.get("reconciliation_stress_score") or 0.0) for r in rows) / max(len(rows), 1)
    total_capital = sum(float(r.get("invested_capital_millions") or 0.0) for r in rows)
    reconcile_count = len([d for d in decisions if d.get("action") == "RECONCILE"])
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
        "reconciliation_score": _round_pct(avg_score),
        "reconciliation_posture": posture,
        "reconciled_capital_millions": _round_money(total_capital),
        "average_reconciliation_stress_score": _round_pct(avg_stress),
        "reconcile_count": reconcile_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "escalate_count": escalate_count,
    }


def _agenda(decisions: list[dict]) -> list[str]:
    agenda = []
    for action_name, text in [
        ("ESCALATE", "Escalate reconciliation exceptions for"),
        ("HOLD", "Hold reconciliation close for"),
        ("REVIEW", "Review reconciliation packet for"),
        ("RECONCILE", "Reconcile live allocation records for"),
    ]:
        items = [d for d in decisions if d.get("action") == action_name][:3]
        if items:
            agenda.append(f"{text} {', '.join(i.get('strategy_id') for i in items)}.")
    if not agenda:
        agenda.append("No reconciliation actions required.")
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    reconciliation_book = _strategy_rows(inputs, policy)
    reconciliation_decisions = _decisions(reconciliation_book, policy)
    overview = _overview(reconciliation_book, reconciliation_decisions)
    return {
        "mission": "QNT30675",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_reconciliation_overview": overview,
        "reconciliation_book": reconciliation_book,
        "reconciliation_decisions": reconciliation_decisions,
        "reconciliation_dependencies": {
            "settlement_latest_run": _latest_run(inputs["settlement"]),
            "finalization_latest_run": _latest_run(inputs["finalization"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "clearance_latest_run": _latest_run(inputs["clearance"]),
            "release_latest_run": _latest_run(inputs["release"]),
            "dispatch_latest_run": _latest_run(inputs["dispatch"]),
            "treasury_latest_run": _latest_run(inputs["treasury"]),
            "mobility_latest_run": _latest_run(inputs["mobility"]),
            "broker_settings": inputs["broker"].get("settings") or {},
        },
        "reconciliation_agenda": _agenda(reconciliation_decisions),
    }


@router.get("/api/live-allocation-reconciliation-command/summary")
def live_allocation_reconciliation_command_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-reconciliation-command/run")
def live_allocation_reconciliation_command_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_reconciliation_overview") or {}
    run = {
        "run_id": f"larc_{time.time_ns()}",
        "mission": "QNT30675",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "reconciliation_posture": overview.get("reconciliation_posture"),
        "reconciliation_score": overview.get("reconciliation_score"),
        "reconcile_count": overview.get("reconcile_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "reconciled_capital_millions": overview.get("reconciled_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-reconciliation-command/audit")
def live_allocation_reconciliation_command_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30675",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-reconciliation-command/policy")
def live_allocation_reconciliation_command_policy(payload: dict = Body(...)):
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
