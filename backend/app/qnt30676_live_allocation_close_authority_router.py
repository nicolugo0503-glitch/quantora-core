from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-close-authority"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CLOSE_DIR = ARTIFACTS_DIR / "live_allocation_close_authority"

DEFAULT_POLICY = {
    "minimum_close_score": 86.0,
    "minimum_reconciliation_score": 84.0,
    "minimum_settlement_score": 84.0,
    "minimum_finalization_score": 83.0,
    "minimum_documentation_completion_pct": 92.0,
    "maximum_exception_pressure": 24.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    CLOSE_DIR.mkdir(parents=True, exist_ok=True)
    return CLOSE_DIR / f"{_safe(email)}.json"


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
        "reconciliation": _read_json(_artifact_file("live_allocation_reconciliation_command", email), {"policy": {}, "runs": []}),
        "settlement": _read_json(_artifact_file("live_allocation_settlement_command", email), {"policy": {}, "runs": []}),
        "finalization": _read_json(_artifact_file("live_allocation_finalization_authority", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "clearance": _read_json(_artifact_file("live_allocation_clearance_grid", email), {"policy": {}, "runs": []}),
        "release": _read_json(_artifact_file("live_allocation_release_authority_mesh", email), {"policy": {}, "runs": []}),
        "dispatch": _read_json(_artifact_file("capital_dispatch_supervision_layer", email), {"policy": {}, "runs": []}),
        "treasury": _read_json(_artifact_file("sovereign_treasury_command", email), {"policy": {}, "runs": []}),
        "mobility": _read_json(_artifact_file("capital_mobility_control_plane", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "broker": _read_json(_artifact_file("broker_integration_layer", email), {"settings": {}, "orders": [], "fills": [], "positions": {}}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "onboarding": _read_json(_artifact_file("investor_onboarding", email), {"investors": []}),
    }


def _investor_map(inputs: dict) -> dict:
    return {row.get("investor_id"): row for row in (inputs["onboarding"].get("investors") or []) if row.get("investor_id")}


def _close_rows(inputs: dict, policy: dict) -> list[dict]:
    reconciliation_run = _latest_run(inputs["reconciliation"])
    settlement_run = _latest_run(inputs["settlement"])
    finalization_run = _latest_run(inputs["finalization"])
    continuity_run = _latest_run(inputs["continuity"])
    clearance_run = _latest_run(inputs["clearance"])
    release_run = _latest_run(inputs["release"])
    dispatch_run = _latest_run(inputs["dispatch"])
    treasury_run = _latest_run(inputs["treasury"])
    mobility_run = _latest_run(inputs["mobility"])
    compliance_run = _latest_run(inputs["compliance"])
    allocations = inputs["execution"].get("strategy_allocations") or []
    accounts = inputs["ledger"].get("accounts") or []
    orders = inputs["broker"].get("orders") or []
    fills = inputs["broker"].get("fills") or []
    positions = inputs["pnl"].get("positions") or []
    investor_map = _investor_map(inputs)

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

    total_cash = sum(float(a.get("cash_balance") or a.get("available_cash") or 0.0) for a in accounts)
    rec_score = float(reconciliation_run.get("reconciliation_score") or 82.0)
    settle_score = float(settlement_run.get("settlement_score") or 82.0)
    final_score = float(finalization_run.get("finalization_score") or 82.0)
    continuity_score = float(continuity_run.get("continuity_score") or 80.0)
    clearance_score = float(clearance_run.get("clearance_score") or 82.0)
    release_score = float(release_run.get("release_score") or 82.0)
    dispatch_score = float(dispatch_run.get("dispatch_score") or 81.0)
    treasury_score = float(treasury_run.get("treasury_score") or 80.0)
    mobility_score = float(mobility_run.get("mobility_score") or 79.0)
    compliance_release = float(compliance_run.get("release_score") or 86.0)
    live_mode_bonus = 6.0 if str((inputs["broker"].get("settings") or {}).get("mode") or "").lower() == "live" else -4.0

    rows = []
    for idx, alloc in enumerate(base):
        strategy_id = str(alloc.get("strategy_id") or f"STRAT_{idx+1:02d}")
        sleeve_id = str(alloc.get("sleeve_id") or strategy_id)
        investor_id = alloc.get("investor_id")
        investor = investor_map.get(investor_id) or {}
        investor_name = alloc.get("investor_name") or investor.get("investor_name") or investor_id or f"Allocator {idx+1}"
        allocated_capital = float(alloc.get("allocated_capital") or 0.0)
        strategy_orders = [o for o in orders if str(o.get("strategy_id") or o.get("sleeve_id") or "") in {strategy_id, sleeve_id}]
        strategy_fills = [f for f in fills if str(f.get("strategy_id") or f.get("sleeve_id") or "") in {strategy_id, sleeve_id}]
        strategy_positions = [p for p in positions if str(p.get("strategy_id") or p.get("sleeve_id") or "") in {strategy_id, sleeve_id}]
        documented_checklist = investor.get("checklist") or {}
        documentation_completion_pct = (sum(1 for v in documented_checklist.values() if v) / max(len(documented_checklist), 1) * 100.0) if documented_checklist else max(88.0, 96.0 - idx * 1.4)
        fill_count = len(strategy_fills)
        order_count = len(strategy_orders)
        position_count = len(strategy_positions)
        close_readiness_pct = min(100.0, 55.0 + fill_count * 10.0 + position_count * 6.0 + (8.0 if order_count else 0.0))
        cash_coverage_pct = min(100.0, (total_cash / max(allocated_capital * 0.15, 1.0)) * 100.0) if allocated_capital else 100.0
        exception_pressure = max(0.0, 100.0 - documentation_completion_pct) * 0.18
        exception_pressure += max(0.0, 90.0 - close_readiness_pct) * 0.22
        exception_pressure += max(0.0, 88.0 - cash_coverage_pct) * 0.15
        exception_pressure += max(0.0, 84.0 - rec_score) * 0.10
        exception_pressure += max(0.0, 84.0 - settle_score) * 0.10
        exception_pressure += max(0.0, 83.0 - final_score) * 0.08
        exception_pressure += max(0.0, 80.0 - continuity_score) * 0.07
        close_score = (
            rec_score * 0.22 + settle_score * 0.20 + final_score * 0.18 + continuity_score * 0.10 +
            clearance_score * 0.08 + release_score * 0.06 + dispatch_score * 0.04 + treasury_score * 0.04 +
            mobility_score * 0.03 + compliance_release * 0.03 + documentation_completion_pct * 0.06 +
            close_readiness_pct * 0.08 + cash_coverage_pct * 0.04 + live_mode_bonus
        )
        close_score = max(0.0, min(100.0, close_score - exception_pressure * 0.35))
        rows.append({
            "strategy_id": strategy_id,
            "strategy_name": alloc.get("strategy_name") or strategy_id,
            "investor_name": investor_name,
            "allocated_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "reconciliation_score": _round_pct(rec_score),
            "settlement_score": _round_pct(settle_score),
            "finalization_score": _round_pct(final_score),
            "continuity_score": _round_pct(continuity_score),
            "documentation_completion_pct": _round_pct(documentation_completion_pct),
            "close_readiness_pct": _round_pct(close_readiness_pct),
            "cash_coverage_pct": _round_pct(cash_coverage_pct),
            "exception_pressure": _round_pct(exception_pressure),
            "close_score": _round_pct(close_score),
        })
    return rows


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        reasons = []
        if row["reconciliation_score"] < float(policy["minimum_reconciliation_score"]):
            reasons.append("reconciliation below threshold")
        if row["settlement_score"] < float(policy["minimum_settlement_score"]):
            reasons.append("settlement below threshold")
        if row["finalization_score"] < float(policy["minimum_finalization_score"]):
            reasons.append("finalization below threshold")
        if row["documentation_completion_pct"] < float(policy["minimum_documentation_completion_pct"]):
            reasons.append("documentation incomplete")
        if row["exception_pressure"] > float(policy["maximum_exception_pressure"]):
            reasons.append("exception pressure elevated")
        if row["close_score"] >= float(policy["minimum_close_score"]) and not reasons:
            action = "CLOSE"
        elif row["close_score"] >= float(policy["minimum_close_score"]) - 4.0:
            action = "REVIEW"
        elif row["close_score"] >= float(policy["minimum_close_score"]) - 10.0:
            action = "HOLD"
        else:
            action = "ESCALATE"
        decisions.append({
            "strategy_id": row["strategy_id"],
            "strategy_name": row["strategy_name"],
            "action": action,
            "close_score": row["close_score"],
            "exception_pressure": row["exception_pressure"],
            "reasons": reasons or ["close authority ready"],
        })
    return decisions


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    avg_score = sum(r["close_score"] for r in rows) / max(len(rows), 1)
    avg_pressure = sum(r["exception_pressure"] for r in rows) / max(len(rows), 1)
    total_capital = sum(r["allocated_capital_millions"] for r in rows)
    counts = {k: 0 for k in ["CLOSE", "REVIEW", "HOLD", "ESCALATE"]}
    for d in decisions:
        counts[d["action"]] = counts.get(d["action"], 0) + 1
    posture = "close"
    if counts["ESCALATE"]:
        posture = "escalate"
    elif counts["HOLD"]:
        posture = "hold"
    elif counts["REVIEW"]:
        posture = "review"
    return {
        "close_score": _round_pct(avg_score),
        "close_posture": posture,
        "close_capital_millions": _round_money(total_capital),
        "average_exception_pressure": _round_pct(avg_pressure),
        "close_count": counts["CLOSE"],
        "review_count": counts["REVIEW"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
    }


def _agenda(decisions: list[dict]) -> list[str]:
    agenda = []
    for action_name, text in [
        ("ESCALATE", "Escalate close authority exceptions for"),
        ("HOLD", "Hold live close authorization for"),
        ("REVIEW", "Review close packet for"),
        ("CLOSE", "Authorize live allocation close for"),
    ]:
        items = [d for d in decisions if d.get("action") == action_name][:3]
        if items:
            agenda.append(f"{text} {', '.join(i.get('strategy_id') for i in items)}.")
    if not agenda:
        agenda.append("No live close actions required.")
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    close_book = _close_rows(inputs, policy)
    close_decisions = _decisions(close_book, policy)
    overview = _overview(close_book, close_decisions)
    return {
        "mission": "QNT30676",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_close_overview": overview,
        "close_book": close_book,
        "close_decisions": close_decisions,
        "close_dependencies": {
            "reconciliation_latest_run": _latest_run(inputs["reconciliation"]),
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
        "close_agenda": _agenda(close_decisions),
    }


@router.get("/api/live-allocation-close-authority/summary")
def live_allocation_close_authority_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-close-authority/run")
def live_allocation_close_authority_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_close_overview") or {}
    run = {
        "run_id": f"laca_{time.time_ns()}",
        "mission": "QNT30676",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "close_posture": overview.get("close_posture"),
        "close_score": overview.get("close_score"),
        "close_count": overview.get("close_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "close_capital_millions": overview.get("close_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-close-authority/audit")
def live_allocation_close_authority_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30676",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-close-authority/policy")
def live_allocation_close_authority_policy(payload: dict = Body(...)):
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
