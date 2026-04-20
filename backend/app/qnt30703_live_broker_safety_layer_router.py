from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-broker-safety-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
LAYER_DIR = ARTIFACTS_DIR / "live_broker_safety_layer"

DEFAULT_POLICY = {
    "max_position_size_pct": 0.02,
    "max_risk_per_trade_pct": 0.01,
    "max_daily_drawdown_pct": 0.05,
    "max_total_open_exposure_pct": 0.65,
    "max_strategy_exposure_pct": 0.25,
    "max_symbol_exposure_pct": 0.12,
    "max_correlation_stack": 2,
    "min_readiness_score": 80.0,
    "require_stop_loss": True,
    "require_take_profit": False,
    "simulation_slippage_bps": 10.0,
}

DEFAULT_CONTROLS = {
    "kill_switch": False,
    "execution_paused": False,
    "operator_override_required": False,
    "broker_connection_required": False,
}

DEMO_EMAIL = "operator@quantora.test"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    LAYER_DIR.mkdir(parents=True, exist_ok=True)
    return LAYER_DIR / f"{_safe(email)}.json"


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
            "controls": dict(DEFAULT_CONTROLS),
            "runs": [],
            "trade_checks": [],
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


def _latest_run(store_or_payload: dict) -> dict:
    runs = store_or_payload.get("runs") or []
    return runs[0] if runs else {}


def _capital_base(email: str) -> dict:
    ledger = _read_json(_artifact_file("investor_capital_ledger", email), {"entries": [], "allocations": [], "accounts": []})
    user_ledger = _read_json(_artifact_file("user_ledgers", email), {"balance": 0.0, "available": 0.0, "allocated": 0.0, "history": []})
    allocations = ledger.get("allocations") or []
    accounts = ledger.get("accounts") or []
    ledger_allocated = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in allocations)
    account_capital = sum(float(a.get("committed_capital") or a.get("capital") or a.get("balance") or 0.0) for a in accounts)
    user_balance = float(user_ledger.get("balance") or 0.0)
    base = max(ledger_allocated, account_capital, user_balance, 1.0)
    return {
        "capital_base": base,
        "ledger": ledger,
        "user_ledger": user_ledger,
    }


def _execution_inputs(email: str) -> dict:
    return {
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"runs": []}),
        "allocation": _read_json(_artifact_file("cross_fund_allocation", email), {"runs": []}),
        "broker": _read_json(_artifact_file("broker_integration_layer", email), {"accounts": [], "orders": [], "runs": []}),
        "autonomy": _read_json(_artifact_file("autonomous_fund_mode", email), {"runs": []}),
        "drawdown_defense": _read_json(_artifact_file("drawdown_defense_system", email), {"runs": []}),
    }


def _readiness_snapshot(inputs: dict, capital_base: float, policy: dict, controls: dict) -> dict:
    execution = inputs["execution"]
    pnl = inputs["pnl"]
    governance_run = _latest_run(inputs["governance"])
    autonomy_run = _latest_run(inputs["autonomy"])
    drawdown_run = _latest_run(inputs["drawdown_defense"])

    trades = execution.get("trades") or []
    allocations = execution.get("strategy_allocations") or []
    positions = pnl.get("positions") or []
    pnl_ledger = pnl.get("ledger") or []

    open_notional = sum(float(t.get("notional") or 0.0) for t in trades if (t.get("status") or "").lower() in {"open", "submitted", "accepted", "new", "partially_filled"})
    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger) + sum(float(p.get("realized_pnl") or 0.0) for p in positions)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(capital_base, 1.0)

    system_health_score = 100.0
    if not trades:
        system_health_score -= 18.0
    if not allocations:
        system_health_score -= 12.0
    if not positions:
        system_health_score -= 12.0
    if controls.get("kill_switch"):
        system_health_score -= 25.0
    if controls.get("execution_paused"):
        system_health_score -= 10.0

    data_integrity_score = 100.0
    null_fields = 0
    for trade in trades:
        if trade.get("symbol") in {None, ""} or trade.get("qty") in {None, ""}:
            null_fields += 1
    if null_fields:
        data_integrity_score -= min(40.0, null_fields * 8.0)
    if capital_base <= 1.0:
        data_integrity_score -= 30.0

    strategy_validation_score = 100.0 if trades and allocations else 68.0
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 76.0)
    autonomy_score = float(autonomy_run.get("autonomy_score") or 72.0)
    defense_score = float(drawdown_run.get("defense_score") or drawdown_run.get("drawdown_defense_score") or 72.0)

    readiness_score = max(0.0, min(100.0,
        system_health_score * 0.20 +
        data_integrity_score * 0.18 +
        strategy_validation_score * 0.18 +
        governance_score * 0.18 +
        autonomy_score * 0.12 +
        defense_score * 0.14
    ))

    production_ready = (
        readiness_score >= float(policy.get("min_readiness_score") or 80.0)
        and drawdown_pct <= float(policy.get("max_daily_drawdown_pct") or 0.05)
        and not controls.get("kill_switch")
        and not controls.get("execution_paused")
    )

    warnings = []
    if drawdown_pct > float(policy.get("max_daily_drawdown_pct") or 0.05) * 0.75:
        warnings.append("daily drawdown nearing hard limit")
    if open_notional / max(capital_base, 1.0) > float(policy.get("max_total_open_exposure_pct") or 0.65) * 0.85:
        warnings.append("open exposure nearing hard limit")
    if not production_ready:
        warnings.append("production readiness below execution standard")

    return {
        "capital_base": _round_money(capital_base),
        "open_notional": _round_money(open_notional),
        "daily_pnl": _round_money(pnl_total),
        "daily_drawdown_pct": _round_pct(drawdown_pct),
        "system_health_score": _round_pct(system_health_score),
        "data_integrity_score": _round_pct(data_integrity_score),
        "strategy_validation_score": _round_pct(strategy_validation_score),
        "governance_score": _round_pct(governance_score),
        "autonomy_score": _round_pct(autonomy_score),
        "drawdown_defense_score": _round_pct(defense_score),
        "readiness_score": _round_pct(readiness_score),
        "production_ready": production_ready,
        "warnings": warnings,
    }


def _current_exposure(execution: dict) -> dict:
    trades = execution.get("trades") or []
    open_trades = [t for t in trades if (t.get("status") or "").lower() in {"open", "submitted", "accepted", "new", "partially_filled"}]
    total_open_notional = sum(float(t.get("notional") or 0.0) for t in open_trades)
    by_strategy = {}
    by_symbol = {}
    long_count = 0
    short_count = 0
    for trade in open_trades:
        strategy = trade.get("strategy_id") or trade.get("strategy_name") or "unknown"
        symbol = trade.get("symbol") or "UNKNOWN"
        notional = float(trade.get("notional") or 0.0)
        by_strategy[strategy] = by_strategy.get(strategy, 0.0) + notional
        by_symbol[symbol] = by_symbol.get(symbol, 0.0) + notional
        side = (trade.get("side") or "").lower()
        if side == "sell":
            short_count += 1
        else:
            long_count += 1
    return {
        "open_trade_count": len(open_trades),
        "total_open_notional": total_open_notional,
        "by_strategy": by_strategy,
        "by_symbol": by_symbol,
        "long_count": long_count,
        "short_count": short_count,
    }


def _infer_correlation_bucket(symbol: str) -> str:
    text = (symbol or "").upper()
    if text in {"SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN"}:
        return "equity_beta"
    if text.startswith("FX") or text in {"DX1", "EURUSD", "USDJPY", "GBPUSD"}:
        return "macro_fx"
    if text in {"IEF", "TLT", "SHY", "TREASU", "BOND"}:
        return "rates"
    if text in {"BTC", "ETH", "SOL", "CRYPTO"}:
        return "crypto"
    return "idiosyncratic"


def _evaluate_trade_for_email(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    controls = store.get("controls") or dict(DEFAULT_CONTROLS)
    capital = _capital_base(email)
    inputs = _execution_inputs(email)
    readiness = _readiness_snapshot(inputs, capital["capital_base"], policy, controls)
    exposure = _current_exposure(inputs["execution"])

    symbol = (payload.get("symbol") or "UNKNOWN").upper()
    side = (payload.get("side") or "buy").lower()
    qty = float(payload.get("qty") or 0.0)
    price = float(payload.get("price") or payload.get("entry_price") or 0.0)
    stop_loss = payload.get("stop_loss")
    take_profit = payload.get("take_profit")
    strategy_id = payload.get("strategy_id") or payload.get("strategy_name") or "unassigned"
    capital_base = float(readiness.get("capital_base") or 1.0)
    notional = float(payload.get("notional") or (qty * price))

    violations = []
    warnings = []

    if controls.get("kill_switch"):
        violations.append("kill switch engaged")
    if controls.get("execution_paused"):
        violations.append("execution pause active")
    if controls.get("operator_override_required") and not payload.get("operator_override"):
        violations.append("operator override required")
    if not readiness.get("production_ready"):
        violations.append("production readiness gate failed")
    if qty <= 0 or price <= 0 or notional <= 0:
        violations.append("invalid trade sizing inputs")
    if bool(policy.get("require_stop_loss")) and stop_loss in {None, "", 0}:
        violations.append("stop loss missing")
    if bool(policy.get("require_take_profit")) and take_profit in {None, "", 0}:
        violations.append("take profit missing")

    risk_amount = 0.0
    if stop_loss not in {None, "", 0}:
        stop_loss = float(stop_loss)
        per_unit_risk = abs(price - stop_loss)
        risk_amount = per_unit_risk * qty
        if side == "sell" and stop_loss < price:
            warnings.append("short trade stop loss is below entry; verify stop logic")
    else:
        risk_amount = notional * float(policy.get("max_risk_per_trade_pct") or 0.01) * 2.0

    risk_pct = risk_amount / max(capital_base, 1.0)
    position_pct = notional / max(capital_base, 1.0)
    total_open_pct = (float(exposure["total_open_notional"]) + notional) / max(capital_base, 1.0)
    strategy_open_pct = (float(exposure["by_strategy"].get(strategy_id, 0.0)) + notional) / max(capital_base, 1.0)
    symbol_open_pct = (float(exposure["by_symbol"].get(symbol, 0.0)) + notional) / max(capital_base, 1.0)

    if position_pct > float(policy.get("max_position_size_pct") or 0.02):
        violations.append("position size exceeds policy")
    if risk_pct > float(policy.get("max_risk_per_trade_pct") or 0.01):
        violations.append("risk per trade exceeds policy")
    if total_open_pct > float(policy.get("max_total_open_exposure_pct") or 0.65):
        violations.append("total open exposure exceeds policy")
    if strategy_open_pct > float(policy.get("max_strategy_exposure_pct") or 0.25):
        violations.append("strategy exposure exceeds policy")
    if symbol_open_pct > float(policy.get("max_symbol_exposure_pct") or 0.12):
        violations.append("symbol exposure exceeds policy")
    if float(readiness.get("daily_drawdown_pct") or 0.0) > float(policy.get("max_daily_drawdown_pct") or 0.05):
        violations.append("daily drawdown lock active")

    bucket = _infer_correlation_bucket(symbol)
    correlated_existing = 0
    for sym, notional_existing in exposure["by_symbol"].items():
        if float(notional_existing or 0.0) <= 0:
            continue
        if _infer_correlation_bucket(sym) == bucket:
            correlated_existing += 1
    if bucket != "idiosyncratic" and correlated_existing >= int(policy.get("max_correlation_stack") or 2):
        violations.append("correlation stack exceeds policy")

    simulated_slippage = notional * (float(policy.get("simulation_slippage_bps") or 10.0) / 10000.0)
    worst_case_loss = risk_amount + simulated_slippage
    worst_case_loss_pct = worst_case_loss / max(capital_base, 1.0)
    if worst_case_loss_pct > float(policy.get("max_risk_per_trade_pct") or 0.01) * 1.1:
        violations.append("pre-execution simulation worst-case loss exceeds policy")

    risk_score = max(0.0, min(100.0,
        100.0
        - position_pct * 1200.0
        - risk_pct * 2400.0
        - max(total_open_pct - float(policy.get("max_total_open_exposure_pct") or 0.65), 0.0) * 1000.0
        - max(float(readiness.get("daily_drawdown_pct") or 0.0), 0.0) * 400.0
        - len(violations) * 8.0
    ))

    approved = len(violations) == 0
    final_position_size = min(notional, capital_base * float(policy.get("max_position_size_pct") or 0.02))

    result = {
        "approved": approved,
        "symbol": symbol,
        "side": side,
        "strategy_id": strategy_id,
        "capital_base": _round_money(capital_base),
        "notional": _round_money(notional),
        "final_position_size": _round_money(final_position_size),
        "position_size_pct": _round_pct(position_pct),
        "risk_amount": _round_money(risk_amount),
        "risk_pct": _round_pct(risk_pct),
        "total_open_exposure_pct": _round_pct(total_open_pct),
        "strategy_exposure_pct": _round_pct(strategy_open_pct),
        "symbol_exposure_pct": _round_pct(symbol_open_pct),
        "daily_drawdown_pct": _round_pct(readiness.get("daily_drawdown_pct") or 0.0),
        "worst_case_loss": _round_money(worst_case_loss),
        "worst_case_loss_pct": _round_pct(worst_case_loss_pct),
        "risk_score": _round_pct(risk_score),
        "correlation_bucket": bucket,
        "violations": violations,
        "warnings": warnings,
        "controls": controls,
        "readiness": readiness,
        "simulation": {
            "slippage_bps": _round_pct(policy.get("simulation_slippage_bps") or 10.0),
            "simulated_slippage": _round_money(simulated_slippage),
            "worst_case_loss": _round_money(worst_case_loss),
        },
        "evaluated_at": _now_iso(),
    }
    return result


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    controls = store.get("controls") or dict(DEFAULT_CONTROLS)
    capital = _capital_base(email)
    inputs = _execution_inputs(email)
    readiness = _readiness_snapshot(inputs, capital["capital_base"], policy, controls)
    exposure = _current_exposure(inputs["execution"])
    runs = store.get("runs") or []
    checks = store.get("trade_checks") or []
    open_pct = exposure["total_open_notional"] / max(capital["capital_base"], 1.0)

    by_strategy = [
        {
            "strategy_id": key,
            "open_notional": _round_money(value),
            "open_exposure_pct": _round_pct(value / max(capital["capital_base"], 1.0)),
        }
        for key, value in sorted(exposure["by_strategy"].items(), key=lambda item: item[1], reverse=True)
    ]
    by_symbol = [
        {
            "symbol": key,
            "open_notional": _round_money(value),
            "open_exposure_pct": _round_pct(value / max(capital["capital_base"], 1.0)),
        }
        for key, value in sorted(exposure["by_symbol"].items(), key=lambda item: item[1], reverse=True)
    ]

    blocked = sum(1 for c in checks[:50] if not c.get("approved"))
    approved = sum(1 for c in checks[:50] if c.get("approved"))
    posture = "SAFE"
    if controls.get("kill_switch") or controls.get("execution_paused") or not readiness.get("production_ready"):
        posture = "BLOCKED"
    elif open_pct > float(policy.get("max_total_open_exposure_pct") or 0.65) * 0.85 or float(readiness.get("daily_drawdown_pct") or 0.0) > float(policy.get("max_daily_drawdown_pct") or 0.05) * 0.75:
        posture = "CONSTRAINED"

    return {
        "mission": "QNT30703",
        "generated_at": _now_iso(),
        "safety_layer_status": {
            "posture": posture,
            "production_ready": readiness.get("production_ready"),
            "kill_switch": controls.get("kill_switch"),
            "execution_paused": controls.get("execution_paused"),
            "operator_override_required": controls.get("operator_override_required"),
            "capital_base": _round_money(capital["capital_base"]),
            "open_trade_count": exposure.get("open_trade_count"),
            "open_notional": _round_money(exposure.get("total_open_notional")),
            "open_exposure_pct": _round_pct(open_pct),
            "daily_drawdown_pct": _round_pct(readiness.get("daily_drawdown_pct") or 0.0),
            "risk_score": _round_pct(max(0.0, min(100.0, readiness.get("readiness_score") - open_pct * 25.0 - float(readiness.get("daily_drawdown_pct") or 0.0) * 120.0))),
            "approved_trade_checks": approved,
            "blocked_trade_checks": blocked,
        },
        "policy": policy,
        "controls": controls,
        "readiness": readiness,
        "exposure": {
            "open_trade_count": exposure.get("open_trade_count"),
            "long_count": exposure.get("long_count"),
            "short_count": exposure.get("short_count"),
            "total_open_notional": _round_money(exposure.get("total_open_notional")),
            "by_strategy": by_strategy,
            "by_symbol": by_symbol,
        },
        "recent_checks": checks[:15],
        "latest_run": runs[0] if runs else None,
    }


def _bootstrap_demo_for_email(email: str) -> dict:
    capital_base = {
        "email": email,
        "accounts": [
            {"investor_id": "inv_demo_001", "capital": 1250000.0},
            {"investor_id": "inv_demo_002", "capital": 875000.0},
        ],
        "allocations": [
            {"strategy_id": "alpha_core", "allocated_amount": 520000.0},
            {"strategy_id": "macro_fx", "allocated_amount": 340000.0},
            {"strategy_id": "rates_defense", "allocated_amount": 210000.0},
        ],
        "entries": [{"entry_id": "cap_demo_1", "amount": 2125000.0}],
    }
    execution = {
        "email": email,
        "strategy_allocations": [
            {"strategy_id": "alpha_core", "strategy_name": "Alpha Core", "allocated_capital": 520000.0},
            {"strategy_id": "macro_fx", "strategy_name": "Macro FX", "allocated_capital": 340000.0},
            {"strategy_id": "rates_defense", "strategy_name": "Rates Defense", "allocated_capital": 210000.0},
        ],
        "trades": [
            {"trade_id": "trd_demo_1", "strategy_id": "alpha_core", "symbol": "SPY", "side": "buy", "qty": 400.0, "entry_price": 540.0, "notional": 216000.0, "status": "open"},
            {"trade_id": "trd_demo_2", "strategy_id": "macro_fx", "symbol": "DX1", "side": "buy", "qty": 120.0, "entry_price": 110.0, "notional": 13200.0, "status": "open"},
            {"trade_id": "trd_demo_3", "strategy_id": "rates_defense", "symbol": "IEF", "side": "buy", "qty": 900.0, "entry_price": 96.0, "notional": 86400.0, "status": "open"},
        ],
        "history": [],
    }
    pnl = {
        "email": email,
        "positions": [
            {"position_id": "pos_demo_1", "symbol": "SPY", "qty": 400.0, "avg_price": 540.0, "mark_price": 546.0, "realized_pnl": 0.0, "unrealized_pnl": 2400.0},
            {"position_id": "pos_demo_2", "symbol": "DX1", "qty": 120.0, "avg_price": 110.0, "mark_price": 111.0, "realized_pnl": 0.0, "unrealized_pnl": 120.0},
            {"position_id": "pos_demo_3", "symbol": "IEF", "qty": 900.0, "avg_price": 96.0, "mark_price": 96.4, "realized_pnl": 0.0, "unrealized_pnl": 360.0},
        ],
        "ledger": [],
    }
    governance = {"email": email, "runs": [{"governance_score": 91.0, "timestamp": _now_ts()}]}
    autonomy = {"email": email, "runs": [{"autonomy_score": 88.0, "timestamp": _now_ts()}]}
    drawdown = {"email": email, "runs": [{"defense_score": 93.0, "timestamp": _now_ts()}]}
    broker = {"email": email, "accounts": [{"broker": "paper", "status": "connected"}], "orders": [], "runs": [{"routing_score": 90.0, "timestamp": _now_ts()}]}

    for folder, payload in {
        "investor_capital_ledger": capital_base,
        "strategy_execution_engine": execution,
        "investor_pnl_ledger": pnl,
        "execution_governance_command": governance,
        "autonomous_fund_mode": autonomy,
        "drawdown_defense_system": drawdown,
        "broker_integration_layer": broker,
    }.items():
        path = _artifact_file(folder, email)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    store = _load(email)
    store["policy"] = dict(DEFAULT_POLICY)
    store["controls"] = dict(DEFAULT_CONTROLS)
    store["runs"] = []
    store["trade_checks"] = []
    _save(email, store)
    return _summary_for_email(email)


@router.get("/api/live-broker-safety-layer/summary")
def live_broker_safety_layer_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/live-broker-safety-layer/run")
def live_broker_safety_layer_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _summary_for_email(email)
    status = summary.get("safety_layer_status") or {}
    readiness = summary.get("readiness") or {}
    run = {
        "run_id": f"lbl_{time.time_ns()}",
        "mission": "QNT30703",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "posture": status.get("posture"),
        "production_ready": status.get("production_ready"),
        "kill_switch": status.get("kill_switch"),
        "execution_paused": status.get("execution_paused"),
        "open_exposure_pct": status.get("open_exposure_pct"),
        "daily_drawdown_pct": status.get("daily_drawdown_pct"),
        "risk_score": status.get("risk_score"),
        "readiness_score": readiness.get("readiness_score"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.post("/api/live-broker-safety-layer/evaluate-trade")
def live_broker_safety_layer_evaluate_trade(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    result = _evaluate_trade_for_email(email, payload)
    store = _load(email)
    row = dict(result)
    row["check_id"] = f"chk_{time.time_ns()}"
    store.setdefault("trade_checks", []).insert(0, row)
    store["trade_checks"] = store.get("trade_checks", [])[:250]
    _save(email, store)
    return result


@router.post("/api/live-broker-safety-layer/policy")
def live_broker_safety_layer_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    for key, value in payload.items():
        if key in DEFAULT_POLICY:
            policy[key] = value
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy, "summary": _summary_for_email(email)}


@router.post("/api/live-broker-safety-layer/controls")
def live_broker_safety_layer_controls(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    controls = store.get("controls") or dict(DEFAULT_CONTROLS)
    for key, value in payload.items():
        if key in DEFAULT_CONTROLS:
            controls[key] = bool(value)
    store["controls"] = controls
    _save(email, store)
    return {"status": "updated", "controls": controls, "summary": _summary_for_email(email)}


@router.post("/api/live-broker-safety-layer/bootstrap-demo")
def live_broker_safety_layer_bootstrap_demo(payload: dict = Body(default=None)):
    session_email = None
    try:
        session_email = _require_user().get("email")
    except HTTPException:
        pass
    email = (payload or {}).get("email") or session_email or DEMO_EMAIL
    return {"status": "bootstrapped", "summary": _bootstrap_demo_for_email(email)}
