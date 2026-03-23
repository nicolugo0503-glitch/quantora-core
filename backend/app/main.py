import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
FRONTEND_DIR = PROJECT_DIR / "frontend"

app = FastAPI(title="Quantora QNT30324C Broker Capital Metrics Normalization", version="30324C")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

ADMIN_EMAILS = {"admin@quantora.local", "nicolugo0503@gmail.com"}
PRICE_BOOK = {
    "AAPL": 180.0,
    "TSLA": 175.0,
    "SPY": 510.0,
    "NVDA": 910.0,
    "MSFT": 420.0,
    "AMZN": 185.0,
    "META": 505.0,
}
ACTIVE_ORDER_STATUSES = {"filled", "accepted", "submitted", "new", "partially_filled", "held_for_orders"}
ADMIN_EMAILS_NORMALIZED = {e.strip().lower() for e in ADMIN_EMAILS}


def normalize_email(value):
    return (value or "").strip().lower()


def user_is_admin_email(email):
    return normalize_email(email) in ADMIN_EMAILS_NORMALIZED


def as_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def empty_session():
    return {"logged_in": False, "display_name": None, "operator_id": None, "email": None, "is_admin": False}


def default_users_data():
    return {"users": []}


def default_policies_data():
    return {
        "policies": [
            {"policy_id": "POL-001", "name": "Large capital changes require approval", "policy_type": "capital_change", "threshold": 5000, "enabled": True},
            {"policy_id": "POL-002", "name": "Fleet run-all requires approval", "policy_type": "run_all", "threshold": 1, "enabled": True},
            {"policy_id": "POL-003", "name": "Loop start below 300s requires approval", "policy_type": "loop_start", "threshold": 300, "enabled": True},
        ]
    }


def default_approvals_data():
    return {"requests": []}


def session_view(data):
    session = {**empty_session(), **(data or {})}
    session["email"] = (session.get("email") or None)
    session["is_admin"] = bool(session.get("is_admin") or user_is_admin_email(session.get("email")))
    return session


def seed_artifacts():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    defaults = {
        "users.json": default_users_data(),
        "session.json": empty_session(),
        "policy_engine.json": default_policies_data(),
        "approval_queue.json": default_approvals_data(),
        "governance_ledger.json": {"events": []},
        "broker_config.json": default_broker_config(),
    }
    for filename, fallback in defaults.items():
        path = ARTIFACTS_DIR / filename
        if not path.exists():
            path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")


# -------------------------
# Generic utilities
# -------------------------
def now_dt():
    return datetime.datetime.utcnow().replace(microsecond=0)


def now_iso():
    return now_dt().isoformat() + "Z"


def load_json(filename, fallback):
    path = ARTIFACTS_DIR / filename
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(filename, data):
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")


def users_db():
    return load_json("users.json", default_users_data())


def save_users(data):
    save_json("users.json", data)


def get_session():
    return session_view(load_json("session.json", empty_session()))


def save_session(data):
    save_json("session.json", session_view(data))


def get_policies():
    return load_json("policy_engine.json", default_policies_data())


def save_policies(data):
    save_json("policy_engine.json", data)


def get_approvals():
    return load_json("approval_queue.json", default_approvals_data())


def save_approvals(data):
    save_json("approval_queue.json", data)


def append_governance_event(actor_email, actor_operator_id, action, target, details=None, category="governance"):
    ledger = load_json("governance_ledger.json", {"events": []})
    event = {
        "event_id": f"gov_{uuid.uuid4().hex[:10]}",
        "timestamp": now_iso(),
        "category": category,
        "actor_email": actor_email,
        "actor_operator_id": actor_operator_id,
        "action": action,
        "target": target,
        "details": details or {},
    }
    ledger["events"].insert(0, event)
    ledger["events"] = ledger["events"][:2000]
    save_json("governance_ledger.json", ledger)
    return event


def require_auth():
    session = get_session()
    if not session.get("logged_in"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def require_admin():
    session = require_auth()
    if not session.get("is_admin") and not user_is_admin_email(session.get("email")):
        raise HTTPException(status_code=403, detail="Admin access required")
    return session_view(session)


def state_filename(operator_id):
    return f"operator_state_{operator_id}.json"


def default_strategy_metrics(strategy_id, symbol="AAPL"):
    price = get_price(symbol)
    return {
        "strategy_id": strategy_id,
        "orders_count": 0,
        "buy_orders": 0,
        "sell_orders": 0,
        "closed_trades": 0,
        "wins": 0,
        "losses": 0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "gross_notional": 0.0,
        "current_position_qty": 0.0,
        "avg_entry_price": 0.0,
        "current_market_value": 0.0,
        "capital_in_use": 0.0,
        "last_price": price,
        "last_run_at": None,
        "last_order_at": None,
        "last_signal_at": None,
        "win_rate": 0.0,
    }


def default_risk_engine():
    return {
        "enabled": True,
        "max_position_notional": 5000.0,
        "max_total_exposure": 20000.0,
        "max_drawdown_pct": 12.0,
        "max_daily_loss": 1500.0,
        "max_orders_per_run": 3,
        "require_broker_for_alpaca": True,
        "auto_shutdown_on_breach": True,
        "kill_switch_active": False,
        "breached": False,
        "breach_count": 0,
        "last_breach": None,
        "last_breach_reason": None,
        "last_evaluated_at": None,
        "peak_equity": 0.0,
        "current_equity": 0.0,
        "current_drawdown_pct": 0.0,
        "day_start_date": now_dt().date().isoformat(),
        "day_start_realized_pnl": 0.0,
        "current_daily_realized_pnl": 0.0,
        "current_total_exposure": 0.0,
    }


def default_capital_source():
    return {
        "mode": "internal",
        "provider": "alpaca",
        "last_updated_at": None,
        "last_updated_by": None,
    }


def default_operator_state(operator_id, display_name):
    return {
        "operator_id": operator_id,
        "display_name": display_name,
        "capital_decision": {"approved": True, "capital_allocated": 16195},
        "strategies": {"strategies": []},
        "strategy_engine": {
            "metrics": {},
            "logs": [],
            "last_engine_run_at": None,
            "last_engine_status": "idle",
        },
        "risk_engine": default_risk_engine(),
        "capital_source": default_capital_source(),
        "orders": {"orders": []},
        "allocator_caps": {
            "operator": {
                "operator_id": operator_id,
                "allocated_capital": 0.0,
                "status": "UNFUNDED",
                "updated_at": None,
            }
        },
        "strategy_loop": {
            "running": False,
            "execution_mode": "internal",
            "interval_seconds": 60,
            "last_run_at": None,
            "next_run_at": None,
            "heartbeat_at": None,
            "total_runs": 0,
            "total_signals": 0,
            "total_orders": 0,
        },
        "monitoring": {
            "latest_snapshot": {},
            "alerts": [],
            "last_evaluated_at": None,
        },
    }


def get_price(symbol):
    return PRICE_BOOK.get((symbol or "").upper(), 100.0)


def strategy_log(state, strategy_id, event_type, message, data=None):
    state.setdefault("strategy_engine", {}).setdefault("logs", [])
    entry = {
        "log_id": f"log_{uuid.uuid4().hex[:10]}",
        "timestamp": now_iso(),
        "strategy_id": strategy_id,
        "event_type": event_type,
        "message": message,
        "data": data or {},
    }
    state["strategy_engine"]["logs"].insert(0, entry)
    state["strategy_engine"]["logs"] = state["strategy_engine"]["logs"][:500]
    return entry


def fill_price(order):
    qty = float(order.get("qty") or 0)
    if qty <= 0:
        return get_price(order.get("symbol", "AAPL"))
    notional = float(order.get("notional") or 0)
    return round(notional / qty, 6) if notional else get_price(order.get("symbol", "AAPL"))


def refresh_metric_market_values(metric, symbol):
    current_price = get_price(symbol)
    position_qty = float(metric.get("current_position_qty") or 0)
    avg_entry = float(metric.get("avg_entry_price") or 0)
    metric["last_price"] = current_price
    metric["current_market_value"] = round(abs(position_qty) * current_price, 2)
    metric["capital_in_use"] = metric["current_market_value"]
    if position_qty > 0:
        metric["unrealized_pnl"] = round((current_price - avg_entry) * position_qty, 2)
    elif position_qty < 0:
        metric["unrealized_pnl"] = round((avg_entry - current_price) * abs(position_qty), 2)
    else:
        metric["unrealized_pnl"] = 0.0
    closed = int(metric.get("closed_trades") or 0)
    wins = int(metric.get("wins") or 0)
    metric["win_rate"] = round((wins / closed) * 100, 2) if closed > 0 else 0.0
    return metric


def apply_trade_to_metric(metric, side, qty, executed_price):
    current_qty = float(metric.get("current_position_qty") or 0)
    avg_entry = float(metric.get("avg_entry_price") or 0)
    delta = qty if side == "buy" else -qty

    metric["orders_count"] = int(metric.get("orders_count") or 0) + 1
    metric["gross_notional"] = round(float(metric.get("gross_notional") or 0) + abs(qty * executed_price), 2)
    metric["last_order_at"] = now_iso()
    metric["last_signal_at"] = metric["last_order_at"]
    if side == "buy":
        metric["buy_orders"] = int(metric.get("buy_orders") or 0) + 1
    else:
        metric["sell_orders"] = int(metric.get("sell_orders") or 0) + 1

    if current_qty == 0 or current_qty * delta > 0:
        new_qty = current_qty + delta
        if current_qty == 0:
            avg_entry = executed_price
        else:
            avg_entry = ((abs(current_qty) * avg_entry) + (abs(delta) * executed_price)) / max(abs(new_qty), 1e-9)
        current_qty = new_qty
    else:
        close_qty = min(abs(current_qty), abs(delta))
        realized_delta = close_qty * ((executed_price - avg_entry) if current_qty > 0 else (avg_entry - executed_price))
        metric["realized_pnl"] = round(float(metric.get("realized_pnl") or 0) + realized_delta, 2)
        if close_qty > 0:
            metric["closed_trades"] = int(metric.get("closed_trades") or 0) + 1
            if realized_delta > 0:
                metric["wins"] = int(metric.get("wins") or 0) + 1
            elif realized_delta < 0:
                metric["losses"] = int(metric.get("losses") or 0) + 1
        remaining_qty = current_qty + delta
        if remaining_qty == 0:
            current_qty = 0
            avg_entry = 0.0
        elif current_qty * remaining_qty < 0:
            current_qty = remaining_qty
            avg_entry = executed_price
        else:
            current_qty = remaining_qty

    metric["current_position_qty"] = round(current_qty, 6)
    metric["avg_entry_price"] = round(avg_entry, 6) if current_qty != 0 else 0.0
    return metric


def operator_positions_from_orders(state):
    positions = {}
    for order in state.get("orders", {}).get("orders", []):
        if order.get("status") not in ACTIVE_ORDER_STATUSES:
            continue
        symbol = (order.get("symbol") or "UNK").upper()
        qty = float(order.get("qty") or 0)
        if qty == 0:
            continue
        price = fill_price(order)
        side = (order.get("side") or "buy").lower()
        signed = qty if side == "buy" else -qty
        bucket = positions.setdefault(symbol, {"symbol": symbol, "net_qty": 0.0, "last_price": get_price(symbol), "avg_fill": 0.0, "fills": 0})
        bucket["net_qty"] += signed
        bucket["last_price"] = get_price(symbol)
        bucket["avg_fill"] = ((bucket["avg_fill"] * bucket["fills"]) + price) / (bucket["fills"] + 1)
        bucket["fills"] += 1
    rows = []
    total = 0.0
    for symbol, bucket in positions.items():
        exposure = round(abs(bucket["net_qty"]) * bucket["last_price"], 2)
        total += exposure
        rows.append({
            "symbol": symbol,
            "net_qty": round(bucket["net_qty"], 6),
            "last_price": bucket["last_price"],
            "market_value": exposure,
        })
    rows.sort(key=lambda x: x["symbol"])
    return rows, round(total, 2)


def operator_exposure(state):
    positions, total = operator_positions_from_orders(state)
    return {"notional": total, "positions": positions, "orders": len(state.get("orders", {}).get("orders", []))}


def migrate_operator_state(state, operator_id=None, display_name=None):
    state.setdefault("operator_id", operator_id or state.get("operator_id"))
    state.setdefault("display_name", display_name or state.get("display_name") or "Operator")
    state.setdefault("strategies", {"strategies": []})
    state.setdefault("orders", {"orders": []})
    state.setdefault("allocator_caps", {"operator": {"operator_id": state.get("operator_id"), "allocated_capital": 0.0, "status": "UNFUNDED", "updated_at": None}})
    state.setdefault("strategy_loop", {"running": False, "execution_mode": "internal", "interval_seconds": 60, "last_run_at": None, "next_run_at": None, "heartbeat_at": None, "total_runs": 0, "total_signals": 0, "total_orders": 0})
    state.setdefault("monitoring", {"latest_snapshot": {}, "alerts": [], "last_evaluated_at": None})
    capital_source = state.setdefault("capital_source", default_capital_source())
    capital_source.setdefault("mode", "internal")
    capital_source.setdefault("provider", "alpaca")
    capital_source.setdefault("last_updated_at", None)
    capital_source.setdefault("last_updated_by", None)
    risk = state.setdefault("risk_engine", default_risk_engine())
    risk.setdefault("enabled", True)
    risk.setdefault("max_position_notional", 5000.0)
    risk.setdefault("max_total_exposure", 20000.0)
    risk.setdefault("max_drawdown_pct", 12.0)
    risk.setdefault("max_daily_loss", 1500.0)
    risk.setdefault("max_orders_per_run", 3)
    risk.setdefault("require_broker_for_alpaca", True)
    risk.setdefault("auto_shutdown_on_breach", True)
    risk.setdefault("kill_switch_active", False)
    risk.setdefault("breached", False)
    risk.setdefault("breach_count", 0)
    risk.setdefault("last_breach", None)
    risk.setdefault("last_breach_reason", None)
    risk.setdefault("last_evaluated_at", None)
    risk.setdefault("peak_equity", 0.0)
    risk.setdefault("current_equity", 0.0)
    risk.setdefault("current_drawdown_pct", 0.0)
    risk.setdefault("day_start_date", now_dt().date().isoformat())
    risk.setdefault("day_start_realized_pnl", 0.0)
    risk.setdefault("current_daily_realized_pnl", 0.0)
    risk.setdefault("current_total_exposure", 0.0)
    engine = state.setdefault("strategy_engine", {})
    engine.setdefault("metrics", {})
    engine.setdefault("logs", [])
    engine.setdefault("last_engine_run_at", None)
    engine.setdefault("last_engine_status", "idle")

    for strategy in state["strategies"].get("strategies", []):
        strategy.setdefault("enabled", True)
        strategy.setdefault("status", "running" if strategy.get("enabled") else "stopped")
        strategy.setdefault("capital_limit", 0.0)
        strategy.setdefault("created_at", now_iso())
        strategy.setdefault("updated_at", strategy.get("created_at"))
        strategy.setdefault("last_action", "created")
        strategy.setdefault("execution_mode", "inherit")
        strategy.setdefault("deleted", False)
        metric = engine["metrics"].setdefault(strategy["strategy_id"], default_strategy_metrics(strategy["strategy_id"], strategy.get("symbol")))
        refresh_metric_market_values(metric, strategy.get("symbol"))

    return state


def ensure_state_for_user(user):
    operator_id = user["operator_id"]
    existing = load_json(state_filename(operator_id), None)
    if existing is None:
        save_json(state_filename(operator_id), default_operator_state(operator_id, user["display_name"]))
    else:
        existing = migrate_operator_state(existing, user.get("operator_id"), user.get("display_name"))
        save_json(state_filename(operator_id), existing)


def get_operator_by_id(operator_id):
    users = users_db()
    user = next((u for u in users["users"] if u["operator_id"] == operator_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found")
    ensure_state_for_user(user)
    return user


def get_operator_state_by_id(operator_id):
    user = get_operator_by_id(operator_id)
    state = load_json(state_filename(operator_id), {})
    state = migrate_operator_state(state, operator_id, user.get("display_name"))
    save_operator_state(state)
    return state


def resolve_operator_context(session):
    session_payload = session_view(session)
    operator_id = session_payload.get("operator_id")
    if operator_id:
        return session_payload
    email = normalize_email(session_payload.get("email"))
    if session_payload.get("logged_in") and email:
        users = users_db()
        user = next((u for u in users.get("users", []) if normalize_email(u.get("email")) == email), None)
        if user:
            repaired = {
                **session_payload,
                "email": user.get("email"),
                "operator_id": user.get("operator_id"),
                "display_name": user.get("display_name"),
                "is_admin": user_is_admin_email(user.get("email")),
                "logged_in": True,
            }
            save_session(repaired)
            return session_view(repaired)
    raise HTTPException(status_code=409, detail="Operator context missing for session")


def get_operator_state(session):
    session_payload = resolve_operator_context(session)
    return get_operator_state_by_id(session_payload.get("operator_id"))


def save_operator_state(state):
    operator_id = state.get("operator_id")
    if not operator_id:
        raise HTTPException(status_code=409, detail="Operator context missing for state")
    save_json(state_filename(operator_id), state)


def policy_for(policy_type):
    for policy in get_policies()["policies"]:
        if policy["policy_type"] == policy_type and policy.get("enabled"):
            return policy
    return None


def broker_positions_exposure(broker_state):
    positions = []
    total = 0.0
    for pos in broker_state.get("positions", []) or []:
        symbol = (pos.get("symbol") or "UNK").upper()
        qty = as_float(pos.get("qty"), 0.0)
        market_value = abs(as_float(pos.get("market_value"), 0.0))
        if market_value <= 0 and qty:
            market_value = round(abs(qty) * get_price(symbol), 2)
        last_price = as_float(pos.get("current_price"), get_price(symbol))
        positions.append({
            "symbol": symbol,
            "net_qty": round(qty, 6),
            "last_price": last_price,
            "market_value": round(market_value, 2),
        })
        total += market_value
    positions.sort(key=lambda x: x["symbol"])
    return positions, round(total, 2)


def build_capital_context(state):
    source = state.setdefault("capital_source", default_capital_source())
    mode = (source.get("mode") or "internal").lower()
    provider = (source.get("provider") or "alpaca").lower()
    if mode == "broker":
        broker_state = refresh_alpaca_state(soft=True)
        account = broker_state.get("account", {}) or {}
        positions, used_capital = broker_positions_exposure(broker_state)
        equity = round(as_float(account.get("equity"), 0.0), 2)
        cash = round(as_float(account.get("cash"), 0.0), 2)
        buying_power = round(as_float(account.get("buying_power") or account.get("regt_buying_power") or account.get("cash"), 0.0), 2)
        if broker_state.get("connected") or equity > 0 or used_capital > 0 or buying_power > 0:
            allocated = equity
            utilization = round((used_capital / allocated) * 100, 2) if allocated > 0 else 0.0
            return {
                "mode": "broker",
                "provider": provider,
                "label": "alpaca" if provider == "alpaca" else provider,
                "allocated_capital": allocated,
                "used_capital": used_capital,
                "remaining_capital": buying_power,
                "utilization_pct": utilization,
                "current_equity": equity,
                "cash": cash,
                "buying_power": buying_power,
                "positions": positions,
                "orders_count": len(broker_state.get("orders", []) or []),
                "connected": bool(broker_state.get("connected")),
                "valid": True,
                "reason": None,
                "broker": broker_state,
            }
        return {
            "mode": "broker",
            "provider": provider,
            "label": "alpaca" if provider == "alpaca" else provider,
            "allocated_capital": 0.0,
            "used_capital": 0.0,
            "remaining_capital": 0.0,
            "utilization_pct": 0.0,
            "current_equity": 0.0,
            "cash": 0.0,
            "buying_power": 0.0,
            "positions": [],
            "orders_count": 0,
            "connected": False,
            "valid": False,
            "reason": "Broker capital mode selected but broker snapshot is unavailable",
            "broker": broker_state,
        }

    exposure = operator_exposure(state)
    allocated = round(as_float(state["allocator_caps"]["operator"].get("allocated_capital"), 0.0), 2)
    used_capital = round(as_float(exposure["notional"], 0.0), 2)
    remaining = round(allocated - used_capital, 2)
    return {
        "mode": "internal",
        "provider": "internal",
        "label": "internal",
        "allocated_capital": allocated,
        "used_capital": used_capital,
        "remaining_capital": remaining,
        "utilization_pct": round((used_capital / allocated) * 100, 2) if allocated > 0 else 0.0,
        "current_equity": allocated,
        "cash": remaining,
        "buying_power": remaining,
        "positions": exposure["positions"],
        "orders_count": exposure["orders"],
        "connected": True,
        "valid": True,
        "reason": None,
        "broker": None,
    }


def available_operator_capital(state):
    return round(build_capital_context(state).get("remaining_capital", 0.0), 2)


def enforce_capital_guard(state, notional, side, strategy=None):
    if (side or "buy").lower() != "buy":
        return
    capital = build_capital_context(state)
    remaining = round(capital.get("remaining_capital", 0.0), 2)
    allocated = round(capital.get("allocated_capital", 0.0), 2)
    if allocated <= 0:
        strategy_id = strategy.get("strategy_id") if strategy else None
        if strategy_id:
            strategy_log(state, strategy_id, "risk_block", "Buy order blocked: no capital available from selected capital source", {"required": notional, "remaining": remaining, "capital_mode": capital.get("mode")})
        raise HTTPException(status_code=400, detail=f"Capital guard: no capital available from {capital.get('label')} source")
    if notional > remaining:
        strategy_id = strategy.get("strategy_id") if strategy else None
        if strategy_id:
            strategy_log(state, strategy_id, "risk_block", "Buy order blocked: insufficient remaining capital", {"required": notional, "remaining": remaining})
        raise HTTPException(status_code=400, detail=f"Capital guard: required {round(notional,2)} exceeds remaining capital {remaining}")
    if strategy and float(strategy.get("capital_limit") or 0) > 0:
        metric = state.setdefault("strategy_engine", {}).setdefault("metrics", {}).setdefault(strategy["strategy_id"], default_strategy_metrics(strategy["strategy_id"], strategy.get("symbol")))
        strategy_remaining = round(float(strategy.get("capital_limit") or 0) - float(metric.get("capital_in_use") or 0), 2)
        if notional > strategy_remaining:
            strategy_log(state, strategy["strategy_id"], "risk_block", "Buy order blocked: strategy capital limit exceeded", {"required": notional, "remaining": strategy_remaining})
            raise HTTPException(status_code=400, detail=f"Capital guard: strategy limit remaining {strategy_remaining}")


def evaluate_risk_state(state):
    risk = state.setdefault("risk_engine", default_risk_engine())
    risk.setdefault("enabled", True)
    engine = summarize_strategy_engine(state)
    capital = build_capital_context(state)
    allocated = round(as_float(capital.get("allocated_capital"), 0.0), 2)
    used_capital = round(as_float(capital.get("used_capital"), 0.0), 2)
    current_equity = round(as_float(capital.get("current_equity"), allocated), 2)
    today = now_dt().date().isoformat()
    if risk.get("day_start_date") != today:
        risk["day_start_date"] = today
        risk["day_start_realized_pnl"] = round(as_float(engine.get("portfolio_realized_pnl"), 0.0), 2)

    peak_equity = as_float(risk.get("peak_equity"), 0.0)
    if peak_equity <= 0:
        peak_equity = max(current_equity, allocated, 0.0)
    peak_equity = max(peak_equity, current_equity)
    risk["peak_equity"] = round(peak_equity, 2)
    drawdown_pct = round((((peak_equity - current_equity) / peak_equity) * 100) if peak_equity > 0 else 0.0, 2)
    daily_realized_pnl = round(as_float(engine.get("portfolio_realized_pnl"), 0.0) - as_float(risk.get("day_start_realized_pnl"), 0.0), 2)

    breaches = []
    status = "SAFE"
    if not capital.get("valid"):
        status = "UNKNOWN"
    if risk.get("enabled"):
        if risk.get("kill_switch_active"):
            breaches.append("Kill switch active")
        max_total = as_float(risk.get("max_total_exposure"), 0.0)
        if max_total > 0 and used_capital > max_total:
            breaches.append(f"Total exposure {round(used_capital,2)} exceeds max total exposure {round(max_total,2)}")
        max_position = as_float(risk.get("max_position_notional"), 0.0)
        if max_position > 0:
            for pos in capital.get("positions", []):
                if as_float(pos.get("market_value"), 0.0) > max_position:
                    breaches.append(f"{pos['symbol']} exposure {round(as_float(pos.get('market_value'), 0.0),2)} exceeds position limit {round(max_position,2)}")
        max_dd = as_float(risk.get("max_drawdown_pct"), 0.0)
        if max_dd > 0 and drawdown_pct > max_dd:
            breaches.append(f"Drawdown {drawdown_pct}% exceeds limit {round(max_dd,2)}%")
        max_daily_loss = as_float(risk.get("max_daily_loss"), 0.0)
        if max_daily_loss > 0 and daily_realized_pnl < (-1 * max_daily_loss):
            breaches.append(f"Daily realized PnL {daily_realized_pnl} breaches daily loss limit {-round(max_daily_loss,2)}")

    previous_reason = risk.get("last_breach_reason")
    risk["breached"] = bool(breaches)
    risk["current_equity"] = current_equity
    risk["current_drawdown_pct"] = drawdown_pct
    risk["current_daily_realized_pnl"] = daily_realized_pnl
    risk["current_total_exposure"] = used_capital
    risk["last_evaluated_at"] = now_iso()
    if breaches:
        status = "BREACH"
        reason = "; ".join(breaches[:5])
        if reason != previous_reason:
            risk["breach_count"] = int(risk.get("breach_count") or 0) + 1
        risk["last_breach"] = now_iso()
        risk["last_breach_reason"] = reason
        if risk.get("auto_shutdown_on_breach"):
            state["strategy_loop"]["running"] = False
            state["strategy_loop"]["next_run_at"] = None
    elif risk.get("kill_switch_active"):
        status = "LOCKED"
        risk["last_breach_reason"] = "Kill switch active"
    elif not capital.get("valid"):
        risk["last_breach_reason"] = capital.get("reason")
    else:
        risk["last_breach_reason"] = None

    return {
        "status": status,
        "capital_source": {
            "mode": capital.get("mode"),
            "label": capital.get("label"),
            "provider": capital.get("provider"),
            "valid": capital.get("valid"),
            "connected": capital.get("connected"),
            "reason": capital.get("reason"),
        },
        "config": risk,
        "breaches": breaches,
        "totals": {
            "current_total_exposure": used_capital,
            "current_equity": current_equity,
            "current_drawdown_pct": drawdown_pct,
            "current_daily_realized_pnl": daily_realized_pnl,
            "allocated_capital": allocated,
            "remaining_capital": round(as_float(capital.get("remaining_capital"), 0.0), 2),
            "utilization_pct": round(as_float(capital.get("utilization_pct"), 0.0), 2),
        },
        "positions": capital.get("positions", []),
    }


def enforce_risk_guard(state, symbol, side, qty, execution_mode="internal"):
    risk_view = evaluate_risk_state(state)
    risk = risk_view["config"]
    if not risk.get("enabled"):
        return risk_view
    if risk.get("kill_switch_active"):
        raise HTTPException(status_code=400, detail="Risk engine: kill switch active")
    if execution_mode == "alpaca" and risk.get("require_broker_for_alpaca") and not resolved_alpaca_credentials():
        raise HTTPException(status_code=400, detail="Risk engine: Alpaca mode requires broker connectivity")
    if risk_view["breaches"] and risk.get("auto_shutdown_on_breach"):
        raise HTTPException(status_code=400, detail=f"Risk engine breach: {risk_view['breaches'][0]}")

    price = get_price(symbol)
    signed_qty = float(qty) if (side or "buy").lower() == "buy" else (-1 * float(qty))
    positions = {p["symbol"]: p for p in risk_view.get("positions", [])}
    current_qty = float(positions.get(symbol, {}).get("net_qty") or 0)
    current_symbol_notional = round(abs(current_qty) * price, 2)
    projected_qty = current_qty + signed_qty
    projected_symbol_notional = round(abs(projected_qty) * price, 2)
    max_position = float(risk.get("max_position_notional") or 0)
    if max_position > 0 and projected_symbol_notional > max_position:
        raise HTTPException(status_code=400, detail=f"Risk engine: projected {symbol} exposure {projected_symbol_notional} exceeds position limit {round(max_position,2)}")
    max_total = float(risk.get("max_total_exposure") or 0)
    projected_total = round(float(risk_view["totals"]["current_total_exposure"]) - current_symbol_notional + projected_symbol_notional, 2)
    if max_total > 0 and projected_total > max_total:
        raise HTTPException(status_code=400, detail=f"Risk engine: projected total exposure {projected_total} exceeds limit {round(max_total,2)}")
    return risk_view


def evaluate_monitoring(state):
    capital = build_capital_context(state)
    allocated = round(as_float(capital.get("allocated_capital"), 0.0), 2)
    used_capital = round(as_float(capital.get("used_capital"), 0.0), 2)
    utilization = round(as_float(capital.get("utilization_pct"), 0.0), 2)
    alerts = []
    risk_view = evaluate_risk_state(state)
    if not capital.get("valid"):
        alerts.append({"level": "warn", "type": "capital-source", "message": capital.get("reason") or "Capital source unavailable"})
    if used_capital > allocated and allocated > 0:
        alerts.append({"level": "critical", "type": "capital-breach", "message": f"Open exposure {used_capital} exceeds source capital {allocated}"})
    elif utilization >= 80 and allocated > 0:
        alerts.append({"level": "warn", "type": "operator-utilization", "message": f"Operator utilization at {utilization}%"})
    if state["strategy_loop"].get("running") and not state["strategy_loop"].get("heartbeat_at"):
        alerts.append({"level": "warn", "type": "loop-heartbeat", "message": "Loop is marked running without heartbeat"})
    for breach in risk_view.get("breaches", []):
        alerts.append({"level": "critical", "type": "risk-breach", "message": breach})

    engine = state.setdefault("strategy_engine", {})
    metrics = engine.setdefault("metrics", {})
    for strategy in state["strategies"].get("strategies", []):
        metric = metrics.setdefault(strategy["strategy_id"], default_strategy_metrics(strategy["strategy_id"], strategy.get("symbol")))
        refresh_metric_market_values(metric, strategy.get("symbol"))
        if float(strategy.get("capital_limit") or 0) > 0 and float(metric.get("capital_in_use") or 0) > float(strategy.get("capital_limit") or 0):
            alerts.append({
                "level": "warn",
                "type": "strategy-limit",
                "message": f"{strategy['name']} exceeds strategy capital limit",
                "strategy_id": strategy["strategy_id"],
            })

    totals = summarize_strategy_engine(state)
    state["monitoring"]["latest_snapshot"] = {
        "timestamp": now_iso(),
        "order_count": capital.get("orders_count", 0),
        "used_capital": used_capital,
        "allocated_capital": allocated,
        "remaining_capital": round(as_float(capital.get("remaining_capital"), 0.0), 2),
        "utilization_pct": utilization,
        "capital_mode": capital.get("mode"),
        "capital_label": capital.get("label"),
        "alerts_count": len(alerts),
        "strategy_realized_pnl": totals["portfolio_realized_pnl"],
        "strategy_unrealized_pnl": totals["portfolio_unrealized_pnl"],
        "active_strategies": totals["running_strategies"],
        "risk_breached": bool(risk_view.get("breaches")),
        "drawdown_pct": risk_view["totals"].get("current_drawdown_pct", 0),
        "daily_realized_pnl": risk_view["totals"].get("current_daily_realized_pnl", 0),
    }
    state["monitoring"]["alerts"] = alerts
    state["monitoring"]["last_evaluated_at"] = now_iso()
    return state["monitoring"]


def summarize_governance(ledger_events):
    summary = {"total_events": len(ledger_events), "by_category": {}, "by_action": {}}
    for event in ledger_events:
        summary["by_category"][event["category"]] = summary["by_category"].get(event["category"], 0) + 1
        summary["by_action"][event["action"]] = summary["by_action"].get(event["action"], 0) + 1
    return summary


def summarize_strategy_engine(state):
    strategies = [s for s in state.get("strategies", {}).get("strategies", []) if not s.get("deleted")]
    metrics = state.setdefault("strategy_engine", {}).setdefault("metrics", {})
    rows = []
    portfolio_realized = 0.0
    portfolio_unrealized = 0.0
    capital_in_use = 0.0
    for strategy in strategies:
        metric = metrics.setdefault(strategy["strategy_id"], default_strategy_metrics(strategy["strategy_id"], strategy.get("symbol")))
        refresh_metric_market_values(metric, strategy.get("symbol"))
        row = {**strategy, "metrics": metric}
        rows.append(row)
        portfolio_realized += float(metric.get("realized_pnl") or 0)
        portfolio_unrealized += float(metric.get("unrealized_pnl") or 0)
        capital_in_use += float(metric.get("capital_in_use") or 0)
    rows.sort(key=lambda x: x.get("name", ""))
    return {
        "strategies": rows,
        "total_strategies": len(rows),
        "running_strategies": len([r for r in rows if r.get("status") == "running" and r.get("enabled")]),
        "enabled_strategies": len([r for r in rows if r.get("enabled")]),
        "portfolio_realized_pnl": round(portfolio_realized, 2),
        "portfolio_unrealized_pnl": round(portfolio_unrealized, 2),
        "portfolio_capital_in_use": round(capital_in_use, 2),
        "recent_logs": state.setdefault("strategy_engine", {}).setdefault("logs", [])[:40],
    }




def build_performance_snapshot(state):
    engine = summarize_strategy_engine(state)
    risk_view = evaluate_risk_state(state)
    monitoring = evaluate_monitoring(state)
    orders = state.get("orders", {}).get("orders", [])
    strategy_rows = engine.get("strategies", [])
    closed_trades = sum(int((s.get("metrics") or {}).get("closed_trades") or 0) for s in strategy_rows)
    wins = sum(int((s.get("metrics") or {}).get("wins") or 0) for s in strategy_rows)
    losses = sum(int((s.get("metrics") or {}).get("losses") or 0) for s in strategy_rows)
    total_orders = len(orders)
    filled_orders = len([o for o in orders if (o.get("status") or "").lower() in ACTIVE_ORDER_STATUSES])
    capital = build_capital_context(state)
    allocated = float(capital.get("allocated_capital", 0) or 0)
    used = float(capital.get("used_capital", 0) or 0)
    current_equity = float(risk_view.get("totals", {}).get("current_equity", allocated) or allocated)
    operator_score = round((float(engine.get("portfolio_realized_pnl") or 0) * 0.35) + (wins * 3) - (losses * 1.5) - (len(risk_view.get("breaches", [])) * 10), 2)
    recent_orders = list(reversed(orders[:10]))
    equity_curve = [{
        "label": "current",
        "equity": round(current_equity, 2),
        "allocated_capital": round(allocated, 2),
        "realized_pnl": round(float(engine.get("portfolio_realized_pnl") or 0), 2),
        "unrealized_pnl": round(float(engine.get("portfolio_unrealized_pnl") or 0), 2),
    }]
    return {
        "summary": {
            "operator_id": state.get("operator_id"),
            "display_name": state.get("display_name"),
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "closed_trades": closed_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round((wins / closed_trades) * 100, 2) if closed_trades else 0.0,
            "realized_pnl": round(float(engine.get("portfolio_realized_pnl") or 0), 2),
            "unrealized_pnl": round(float(engine.get("portfolio_unrealized_pnl") or 0), 2),
            "capital_in_use": round(float(engine.get("portfolio_capital_in_use") or 0), 2),
            "allocated_capital": round(allocated, 2),
            "used_capital": round(used, 2),
            "utilization_pct": round((used / allocated) * 100, 2) if allocated > 0 else 0.0,
            "current_equity": round(current_equity, 2),
            "capital_mode": capital.get("mode"),
            "capital_label": capital.get("label"),
            "capital_valid": capital.get("valid"),
            "current_drawdown_pct": round(float(risk_view.get("totals", {}).get("current_drawdown_pct") or 0), 2),
            "daily_realized_pnl": round(float(risk_view.get("totals", {}).get("current_daily_realized_pnl") or 0), 2),
            "risk_breaches": len(risk_view.get("breaches", [])),
            "operator_score": operator_score,
        },
        "strategies": [
            {
                "strategy_id": s.get("strategy_id"),
                "name": s.get("name"),
                "symbol": s.get("symbol"),
                "status": s.get("status"),
                "enabled": s.get("enabled"),
                "execution_mode": s.get("execution_mode"),
                "orders_count": (s.get("metrics") or {}).get("orders_count", 0),
                "closed_trades": (s.get("metrics") or {}).get("closed_trades", 0),
                "win_rate": (s.get("metrics") or {}).get("win_rate", 0),
                "realized_pnl": (s.get("metrics") or {}).get("realized_pnl", 0),
                "unrealized_pnl": (s.get("metrics") or {}).get("unrealized_pnl", 0),
                "capital_in_use": (s.get("metrics") or {}).get("capital_in_use", 0),
            }
            for s in strategy_rows
        ],
        "recent_orders": recent_orders,
        "equity_curve": equity_curve,
    }


# -------------------------
# Alpaca broker layer
# -------------------------
def default_broker_config():
    return {
        "alpaca": {
            "base_url": "https://paper-api.alpaca.markets",
            "paper": True,
            "api_key": "",
            "secret_key": "",
            "last_status": "disconnected",
            "last_tested_at": None,
            "last_error": None,
            "account_snapshot": {},
            "positions_snapshot": [],
            "orders_snapshot": [],
        }
    }


def get_broker_config():
    return load_json("broker_config.json", default_broker_config())


def save_broker_config(data):
    save_json("broker_config.json", data)


def mask_secret(value):
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return value[:3] + ("*" * (len(value) - 6)) + value[-3:]


def resolved_alpaca_credentials():
    cfg = get_broker_config()["alpaca"]
    env_key = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID")
    env_secret = os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")
    env_base = os.getenv("ALPACA_BASE_URL")
    if env_key and env_secret:
        base_url = (env_base or cfg.get("base_url") or "https://paper-api.alpaca.markets").rstrip("/")
        return {
            "api_key": env_key,
            "secret_key": env_secret,
            "base_url": base_url,
            "paper": "paper" in base_url,
            "source": "env",
        }
    if cfg.get("api_key") and cfg.get("secret_key"):
        return {
            "api_key": cfg["api_key"],
            "secret_key": cfg["secret_key"],
            "base_url": (cfg.get("base_url") or "https://paper-api.alpaca.markets").rstrip("/"),
            "paper": bool(cfg.get("paper", True)),
            "source": "stored",
        }
    return None


def safe_broker_view(data=None):
    cfg = data or get_broker_config()
    alpaca = cfg["alpaca"]
    creds = resolved_alpaca_credentials()
    source = creds["source"] if creds else "none"
    return {
        "alpaca": {
            "connected": bool(creds),
            "source": source,
            "base_url": (creds or {}).get("base_url", alpaca.get("base_url")),
            "paper": (creds or {}).get("paper", alpaca.get("paper", True)),
            "api_key_masked": mask_secret((creds or {}).get("api_key", alpaca.get("api_key", ""))),
            "secret_key_masked": mask_secret((creds or {}).get("secret_key", alpaca.get("secret_key", ""))),
            "last_status": alpaca.get("last_status", "disconnected"),
            "last_tested_at": alpaca.get("last_tested_at"),
            "last_error": alpaca.get("last_error"),
        }
    }


def alpaca_request(method, path, payload=None, query=None):
    creds = resolved_alpaca_credentials()
    if not creds:
        raise HTTPException(status_code=400, detail="Alpaca credentials not configured")
    url = creds["base_url"].rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {
        "APCA-API-KEY-ID": creds["api_key"],
        "APCA-API-SECRET-KEY": creds["secret_key"],
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        detail = f"Alpaca HTTP {exc.code}: {body[:400]}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Alpaca connectivity error: {exc}")


def refresh_alpaca_state(soft=False):
    cfg = get_broker_config()
    alpaca_cfg = cfg["alpaca"]
    creds = resolved_alpaca_credentials()
    if not creds:
        alpaca_cfg["last_status"] = "disconnected"
        alpaca_cfg["last_error"] = "No credentials configured"
        save_broker_config(cfg)
        return {
            **safe_broker_view(cfg)["alpaca"],
            "account": alpaca_cfg.get("account_snapshot", {}),
            "positions": alpaca_cfg.get("positions_snapshot", []),
            "orders": alpaca_cfg.get("orders_snapshot", []),
            "stale": True,
        }
    try:
        account = alpaca_request("GET", "/v2/account")
        positions = alpaca_request("GET", "/v2/positions")
        orders = alpaca_request("GET", "/v2/orders", query={"status": "open", "direction": "desc", "limit": 50})
        alpaca_cfg["account_snapshot"] = account
        alpaca_cfg["positions_snapshot"] = positions if isinstance(positions, list) else []
        alpaca_cfg["orders_snapshot"] = orders if isinstance(orders, list) else []
        alpaca_cfg["last_status"] = "connected"
        alpaca_cfg["last_tested_at"] = now_iso()
        alpaca_cfg["last_error"] = None
        save_broker_config(cfg)
        return {
            **safe_broker_view(cfg)["alpaca"],
            "account": alpaca_cfg["account_snapshot"],
            "positions": alpaca_cfg["positions_snapshot"],
            "orders": alpaca_cfg["orders_snapshot"],
            "stale": False,
        }
    except HTTPException as exc:
        alpaca_cfg["last_status"] = "error"
        alpaca_cfg["last_tested_at"] = now_iso()
        alpaca_cfg["last_error"] = exc.detail
        save_broker_config(cfg)
        if not soft:
            raise
        return {
            **safe_broker_view(cfg)["alpaca"],
            "account": alpaca_cfg.get("account_snapshot", {}),
            "positions": alpaca_cfg.get("positions_snapshot", []),
            "orders": alpaca_cfg.get("orders_snapshot", []),
            "stale": True,
        }


def normalize_alpaca_order(order, fallback_symbol, fallback_side, fallback_qty):
    qty = float(order.get("qty") or fallback_qty or 0)
    avg_price = float(order.get("filled_avg_price") or order.get("limit_price") or get_price(fallback_symbol))
    return {
        "order_id": f"ord_{uuid.uuid4().hex[:10]}",
        "broker_order_id": order.get("id"),
        "symbol": (order.get("symbol") or fallback_symbol).upper(),
        "side": (order.get("side") or fallback_side).lower(),
        "qty": qty,
        "notional": round(qty * avg_price, 2),
        "status": order.get("status", "submitted"),
        "mode": "alpaca",
        "broker": "alpaca",
        "timestamp": now_iso(),
        "asset_class": order.get("asset_class"),
        "order_type": order.get("type") or order.get("order_type") or "market",
        "time_in_force": order.get("time_in_force") or "day",
        "raw": order,
    }


def alpaca_submit_market_order(symbol, side, qty):
    return alpaca_request(
        "POST",
        "/v2/orders",
        payload={
            "symbol": symbol.upper(),
            "qty": str(qty),
            "side": side.lower(),
            "type": "market",
            "time_in_force": "day",
        },
    )


# -------------------------
# Strategy engine views and execution
# -------------------------
def get_strategy_by_id(state, strategy_id):
    strategy = next((s for s in state.get("strategies", {}).get("strategies", []) if s.get("strategy_id") == strategy_id and not s.get("deleted")), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


def persist_order(state, order):
    state["orders"]["orders"].insert(0, order)
    state["orders"]["orders"] = state["orders"]["orders"][:1000]
    state["strategy_loop"]["total_orders"] = int(state["strategy_loop"].get("total_orders") or 0) + 1


def apply_order_to_strategy(state, strategy, order):
    metrics = state.setdefault("strategy_engine", {}).setdefault("metrics", {})
    metric = metrics.setdefault(strategy["strategy_id"], default_strategy_metrics(strategy["strategy_id"], strategy.get("symbol")))
    metric["last_run_at"] = now_iso()
    apply_trade_to_metric(metric, order["side"], float(order["qty"]), fill_price(order))
    refresh_metric_market_values(metric, strategy.get("symbol"))
    strategy["updated_at"] = now_iso()
    strategy_log(
        state,
        strategy["strategy_id"],
        "execution",
        f"{strategy['name']} executed {order['side']} {order['qty']} {order['symbol']} via {order.get('mode')}",
        {"order_id": order.get("order_id"), "notional": order.get("notional")},
    )
    return metric


def build_internal_order(symbol, side, qty, execution_mode, strategy_id=None):
    return {
        "order_id": f"ord_{uuid.uuid4().hex[:10]}",
        "strategy_id": strategy_id,
        "symbol": symbol.upper(),
        "side": side.lower(),
        "qty": float(qty),
        "notional": round(get_price(symbol.upper()) * float(qty), 2),
        "status": "filled",
        "mode": execution_mode,
        "broker": "internal" if execution_mode == "internal" else execution_mode,
        "timestamp": now_iso(),
    }


def run_strategy_for_state(state, strategy, execution_mode, actor_email, actor_operator_id, source_action):
    strategy_mode = (strategy.get("execution_mode") or "inherit").lower()
    chosen_mode = (execution_mode or "internal").lower() if strategy_mode == "inherit" else strategy_mode
    notional = round(get_price(strategy["symbol"]) * float(strategy["default_qty"]), 2)
    enforce_risk_guard(state, strategy["symbol"], strategy["side"], float(strategy["default_qty"]), chosen_mode)
    enforce_capital_guard(state, notional, strategy["side"], strategy)

    if chosen_mode == "alpaca":
        if not resolved_alpaca_credentials():
            strategy_log(state, strategy["strategy_id"], "broker_error", "Alpaca execution requested but no credentials configured", {})
            raise HTTPException(status_code=400, detail="Alpaca mode requested but no Alpaca credentials are configured")
        broker_order = alpaca_submit_market_order(strategy["symbol"], strategy["side"], strategy["default_qty"])
        order = normalize_alpaca_order(broker_order, strategy["symbol"], strategy["side"], strategy["default_qty"])
    else:
        order = build_internal_order(strategy["symbol"], strategy["side"], strategy["default_qty"], chosen_mode, strategy["strategy_id"])

    order["strategy_id"] = strategy["strategy_id"]
    order["strategy_name"] = strategy["name"]
    persist_order(state, order)
    apply_order_to_strategy(state, strategy, order)
    append_governance_event(actor_email, actor_operator_id, source_action, state["operator_id"], order, "execution")
    return order


def run_strategies_for_state(state, execution_mode, actor_email, actor_operator_id, source_action):
    strategies = [s for s in state.get("strategies", {}).get("strategies", []) if s.get("enabled") and s.get("status") == "running" and not s.get("deleted")]
    executed_orders = []
    state["strategy_loop"]["last_run_at"] = now_iso()
    state["strategy_loop"]["heartbeat_at"] = now_iso()
    state["strategy_loop"]["total_runs"] = int(state["strategy_loop"].get("total_runs") or 0) + 1
    state["strategy_loop"]["total_signals"] = int(state["strategy_loop"].get("total_signals") or 0) + len(strategies)
    engine = state.setdefault("strategy_engine", {})
    engine["last_engine_run_at"] = now_iso()
    engine["last_engine_status"] = "running"

    risk = state.setdefault("risk_engine", default_risk_engine())
    for strategy in strategies:
        if risk.get("enabled") and int(risk.get("max_orders_per_run") or 0) > 0 and len(executed_orders) >= int(risk.get("max_orders_per_run") or 0):
            strategy_log(state, strategy["strategy_id"], "risk_block", "Execution skipped: max orders per run reached", {"max_orders_per_run": risk.get("max_orders_per_run")})
            append_governance_event(actor_email, actor_operator_id, "strategy.execution_blocked", strategy["strategy_id"], {"detail": "Risk engine: max orders per run reached"}, "risk")
            continue
        try:
            executed_orders.append(run_strategy_for_state(state, strategy, execution_mode, actor_email, actor_operator_id, source_action))
        except HTTPException as exc:
            strategy_log(state, strategy["strategy_id"], "execution_blocked", str(exc.detail), {"execution_mode": execution_mode})
            append_governance_event(actor_email, actor_operator_id, "strategy.execution_blocked", strategy["strategy_id"], {"detail": exc.detail}, "risk")

    engine["last_engine_status"] = "completed"
    evaluate_monitoring(state)
    save_operator_state(state)
    return executed_orders


def build_operator_workspace(state):
    monitoring = evaluate_monitoring(state)
    engine = summarize_strategy_engine(state)
    capital = build_capital_context(state)
    save_operator_state(state)
    orders = state["orders"]["orders"][:12]
    return {
        "operator_id": state["operator_id"],
        "display_name": state["display_name"],
        "capital": {
            **state["allocator_caps"]["operator"],
            "allocated_capital": capital.get("allocated_capital", state["allocator_caps"]["operator"].get("allocated_capital", 0)),
            "mode": capital.get("mode", state.get("capital_source", {}).get("mode", "internal")),
            "label": capital.get("label", monitoring["latest_snapshot"].get("capital_label", "internal")),
            "used_capital": capital.get("used_capital", monitoring["latest_snapshot"].get("used_capital", 0)),
            "remaining_capital": capital.get("remaining_capital", monitoring["latest_snapshot"].get("remaining_capital", 0)),
            "utilization_pct": capital.get("utilization_pct", monitoring["latest_snapshot"].get("utilization_pct", 0)),
            "current_equity": capital.get("current_equity", 0),
            "cash": capital.get("cash", 0),
            "buying_power": capital.get("buying_power", 0),
            "valid": capital.get("valid", True),
            "connected": capital.get("connected", True),
        },
        "capital_source": state.get("capital_source", default_capital_source()),
        "strategies": engine,
        "strategy_loop": state["strategy_loop"],
        "orders": orders,
        "positions": operator_positions_from_orders(state)[0],
        "monitoring": monitoring,
        "risk_engine": evaluate_risk_state(state),
        "execution_summary": {
            "recent_orders": len(orders),
            "enabled_strategies": engine["enabled_strategies"],
            "running_strategies": engine["running_strategies"],
            "total_orders": state["strategy_loop"].get("total_orders", 0),
            "realized_pnl": engine["portfolio_realized_pnl"],
            "unrealized_pnl": engine["portfolio_unrealized_pnl"],
        },
    }


def build_top_bar_metrics(snapshot):
    workspace = snapshot.get("personal_workspace", {}) or {}
    capital = workspace.get("capital", {}) or {}
    performance = (snapshot.get("performance", {}) or {}).get("summary", {}) or {}
    broker = snapshot.get("broker", {}) or {}
    account = broker.get("account", {}) or {}
    mode = (capital.get("mode") or snapshot.get("capital_source", {}).get("mode") or "internal").lower()
    label = capital.get("label") or snapshot.get("risk_engine", {}).get("capital_source", {}).get("label") or "internal"

    if mode == "broker":
        return {
            "mode": "broker",
            "source_display": f"broker / {label}",
            "cards": {
                "operator": {"label": "Operator", "value": workspace.get("display_name") or "-"},
                "primary_1": {"label": "Broker Equity", "value": round(as_float(capital.get("current_equity") or account.get("equity"), 0.0), 2)},
                "primary_2": {"label": "Exposure", "value": round(as_float(capital.get("used_capital"), 0.0), 2)},
                "primary_3": {"label": "Buying Power", "value": round(as_float(capital.get("buying_power") or account.get("buying_power") or account.get("regt_buying_power"), 0.0), 2)},
                "strategies": {"label": "Running Strategies", "value": snapshot.get("strategy_engine", {}).get("running_strategies", 0)},
                "pnl": {"label": "Realized PnL", "value": round(as_float(performance.get("realized_pnl"), 0.0), 2)},
                "risk": {"label": "Risk State", "value": snapshot.get("risk_engine", {}).get("status") or "SAFE"},
                "source": {"label": "Broker Cash", "value": round(as_float(capital.get("cash") or account.get("cash"), 0.0), 2)},
            },
        }

    return {
        "mode": "internal",
        "source_display": f"internal / {label}",
        "cards": {
            "operator": {"label": "Operator", "value": workspace.get("display_name") or "-"},
            "primary_1": {"label": "Allocated Capital", "value": round(as_float(capital.get("allocated_capital"), 0.0), 2)},
            "primary_2": {"label": "Used Capital", "value": round(as_float(capital.get("used_capital"), 0.0), 2)},
            "primary_3": {"label": "Remaining Capital", "value": round(as_float(capital.get("remaining_capital"), 0.0), 2)},
            "strategies": {"label": "Running Strategies", "value": snapshot.get("strategy_engine", {}).get("running_strategies", 0)},
            "pnl": {"label": "Realized PnL", "value": round(as_float(performance.get("realized_pnl"), 0.0), 2)},
            "risk": {"label": "Risk State", "value": snapshot.get("risk_engine", {}).get("status") or "SAFE"},
            "source": {"label": "Capital Source", "value": f"internal / {label}"},
        },
    }


def build_command_center_snapshot(session):
    seed_artifacts()
    session_payload = resolve_operator_context(session) if session_view(session).get("logged_in") else session_view(session)
    users = users_db()["users"]
    state = get_operator_state(session_payload)
    workspace = build_operator_workspace(state)
    approvals = get_approvals()["requests"]
    ledger = load_json("governance_ledger.json", {"events": []}).get("events", [])
    pending = [r for r in approvals if r.get("status") == "PENDING"]

    try:
        broker = refresh_alpaca_state(soft=True)
    except Exception as exc:
        broker = {"connected": False, "last_status": "error", "last_error": str(exc), "positions": [], "orders": [], "account": {}, "stale": True}

    try:
        performance = build_performance_snapshot(state)
    except Exception as exc:
        performance = {"status": "degraded", "error": str(exc)}

    governance = {
        "pending_approvals": len(pending),
        "approvals": approvals[:8],
        "policies": get_policies().get("policies", []),
        "ledger_summary": summarize_governance(ledger),
        "recent_events": ledger[:8],
    }
    snapshot = {
        "session": session_payload,
        "north_star": {
            "mission": "QNT30324C Broker Capital Metrics Normalization",
            "system": "Quantora multi-layer institutional trading operating system",
            "timestamp": now_iso(),
        },
        "personal_workspace": workspace,
        "strategy_engine": workspace["strategies"],
        "risk_engine": workspace["risk_engine"],
        "capital_source": workspace.get("capital_source", default_capital_source()),
        "performance": performance,
        "broker": broker,
        "governance": governance,
        "system_health": {
            "status": "ok",
            "registered_users": len(users),
            "policies_enabled": len([p for p in governance["policies"] if p.get("enabled")]),
            "layer": "qnt30324c-broker-capital-metrics-normalization",
            "broker_status": broker.get("last_status"),
            "admin_ready": session_payload.get("is_admin"),
        },
    }
    snapshot["top_bar"] = build_top_bar_metrics(snapshot)
    if session_payload.get("is_admin"):
        try:
            snapshot["control_tower"] = control_tower_view()
        except Exception as exc:
            snapshot["control_tower"] = {"status": "degraded", "error": str(exc), "operators": [], "totals": {}}
    return snapshot


# -------------------------
# Quantora control tower views
# -------------------------
def control_tower_view():
    users = users_db()["users"]
    operators = []
    totals = {"operators": 0, "orders": 0, "allocated_capital": 0.0, "used_capital": 0.0, "alerts": 0, "running_loops": 0, "realized_pnl": 0.0}
    for user in users:
        ensure_state_for_user(user)
        state = load_json(state_filename(user["operator_id"]), {})
        state = migrate_operator_state(state, operator_id, user.get("display_name"))
        monitoring = evaluate_monitoring(state)
        engine = summarize_strategy_engine(state)
        save_operator_state(state)
        capital = build_capital_context(state)
        allocated = float(capital.get("allocated_capital", 0) or 0)
        row = {
            "operator_id": user["operator_id"],
            "display_name": user["display_name"],
            "email": user["email"],
            "orders": len(state["orders"]["orders"]),
            "strategies": engine["total_strategies"],
            "allocated_capital": allocated,
            "used_capital": monitoring["latest_snapshot"].get("used_capital", 0),
            "remaining_capital": monitoring["latest_snapshot"].get("remaining_capital", 0),
            "capital_mode": capital.get("mode"),
            "capital_label": capital.get("label"),
            "loop_running": state["strategy_loop"]["running"],
            "alerts": len(monitoring["alerts"]),
            "execution_mode": state["strategy_loop"].get("execution_mode"),
            "last_run_at": state["strategy_loop"].get("last_run_at"),
            "realized_pnl": engine["portfolio_realized_pnl"],
            "risk_breached": bool(state.get("risk_engine", {}).get("breached")),
        }
        operators.append(row)
        totals["operators"] += 1
        totals["orders"] += row["orders"]
        totals["allocated_capital"] += allocated
        totals["used_capital"] += row["used_capital"]
        totals["alerts"] += row["alerts"]
        totals["realized_pnl"] += row["realized_pnl"]
        if row["loop_running"]:
            totals["running_loops"] += 1
    totals["remaining_capital"] = round(totals["allocated_capital"] - totals["used_capital"], 2)
    totals["realized_pnl"] = round(totals["realized_pnl"], 2)
    return {"operators": operators, "totals": totals}


def submit_approval_request(session, request_type, target, payload, reason):
    queue = get_approvals()
    req = {
        "request_id": f"apr_{uuid.uuid4().hex[:10]}",
        "created_at": now_iso(),
        "created_by_email": session.get("email"),
        "created_by_operator_id": session.get("operator_id"),
        "request_type": request_type,
        "target": target,
        "payload": payload,
        "reason": reason,
        "status": "PENDING",
        "reviewed_at": None,
        "reviewed_by": None,
        "notes": "",
    }
    queue["requests"].insert(0, req)
    queue["requests"] = queue["requests"][:1000]
    save_approvals(queue)
    append_governance_event(session.get("email"), session.get("operator_id"), "approval.requested", target, req, "approval")
    return req


def apply_approval_request(req, admin_session):
    if req["request_type"] == "capital_change":
        state = get_operator_state_by_id(req["target"])
        state["allocator_caps"]["operator"] = {
            "operator_id": req["target"],
            "allocated_capital": req["payload"]["allocated_capital"],
            "status": "FUNDED" if req["payload"]["allocated_capital"] > 0 else "UNFUNDED",
            "updated_at": now_iso(),
        }
        evaluate_monitoring(state)
        save_operator_state(state)
    elif req["request_type"] == "run_all":
        for user in users_db()["users"]:
            ensure_state_for_user(user)
            state = load_json(state_filename(user["operator_id"]), {})
            state = migrate_operator_state(state, operator_id, user.get("display_name"))
            run_strategies_for_state(state, state["strategy_loop"].get("execution_mode", "internal"), admin_session.get("email"), admin_session.get("operator_id"), "approval.run_all.execute")
    elif req["request_type"] == "loop_start":
        state = get_operator_state_by_id(req["target"])
        state["strategy_loop"]["running"] = True
        state["strategy_loop"]["execution_mode"] = req["payload"]["execution_mode"]
        state["strategy_loop"]["interval_seconds"] = int(req["payload"]["interval_seconds"])
        state["strategy_loop"]["heartbeat_at"] = now_iso()
        state["strategy_loop"]["next_run_at"] = (now_dt() + datetime.timedelta(seconds=int(req["payload"]["interval_seconds"]))).isoformat() + "Z"
        save_operator_state(state)
    append_governance_event(admin_session.get("email"), admin_session.get("operator_id"), "approval.approved", req["target"], req, "approval")


# -------------------------
# Request models
# -------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class StrategyRegisterRequest(BaseModel):
    name: str
    symbol: str
    side: str
    default_qty: int
    enabled: bool = True
    capital_limit: float = 0.0
    execution_mode: str = "inherit"


class StrategyToggleRequest(BaseModel):
    strategy_id: str
    enabled: bool


class StrategyLifecycleRequest(BaseModel):
    strategy_id: str
    action: str


class StrategyDeleteRequest(BaseModel):
    strategy_id: str


class OperatorCapitalRequest(BaseModel):
    allocated_capital: float


class AdminOperatorCapitalRequest(BaseModel):
    operator_id: str
    allocated_capital: float


class AdminLoopRequest(BaseModel):
    operator_id: str
    execution_mode: str = "internal"
    interval_seconds: int = 60


class PolicyUpdateRequest(BaseModel):
    policy_id: str
    threshold: float
    enabled: bool = True


class ApprovalDecisionRequest(BaseModel):
    request_id: str
    decision: str
    notes: str = ""


class RunOperatorRequest(BaseModel):
    execution_mode: str = Field(default="internal")


class AlpacaConnectRequest(BaseModel):
    api_key: str
    secret_key: str
    base_url: str = "https://paper-api.alpaca.markets"
    paper: bool = True


class RiskConfigUpdateRequest(BaseModel):
    enabled: bool = True
    max_position_notional: float = 5000.0
    max_total_exposure: float = 20000.0
    max_drawdown_pct: float = 12.0
    max_daily_loss: float = 1500.0
    max_orders_per_run: int = 3
    require_broker_for_alpaca: bool = True
    auto_shutdown_on_breach: bool = True


class RiskKillSwitchRequest(BaseModel):
    active: bool
    note: str = ""


class CapitalSourceUpdateRequest(BaseModel):
    mode: str = "internal"


class ManualOrderRequest(BaseModel):
    symbol: str
    side: str
    qty: float
    execution_mode: str = "internal"


# -------------------------
# Error handling
# -------------------------
def structured_error(status_code, error, reason, detail=None, extra=None):
    payload = {"error": error, "reason": reason, "_http_status": status_code}
    if detail and detail != reason:
        payload["detail"] = detail
    if extra:
        payload.update(extra)
    return payload


def classify_http_error(status_code, detail):
    text = detail if isinstance(detail, str) else json.dumps(detail)
    low = text.lower()
    if status_code == 401:
        return "AUTH_REQUIRED"
    if status_code == 403:
        return "ADMIN_REQUIRED" if "admin" in low else "FORBIDDEN"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 409:
        return "CONFLICT"
    if "risk engine" in low or "kill switch" in low or "risk" in low and "breach" in low:
        return "RISK_BLOCK"
    if "operator context" in low or "operator_id" in low:
        return "OPERATOR_CONTEXT_MISSING"
    if "capital guard" in low:
        return "CAPITAL_GUARD"
    if "alpaca" in low:
        return "BROKER_ERROR"
    if status_code == 422:
        return "VALIDATION_ERROR"
    return "HTTP_ERROR"


@app.on_event("startup")
def startup_event():
    seed_artifacts()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
    error = classify_http_error(exc.status_code, detail)
    return JSONResponse(status_code=exc.status_code, content=structured_error(exc.status_code, error, detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=structured_error(422, "VALIDATION_ERROR", "Request validation failed", extra={"fields": exc.errors()}))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content=structured_error(500, "SYSTEM_ERROR", "Internal Server Error", detail=str(exc)))


# -------------------------
# Core routes
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok", "layer": "qnt30324c-broker-capital-metrics-normalization"}


@app.post("/auth/register")
def auth_register(payload: RegisterRequest):
    users = users_db()
    email = normalize_email(payload.email)
    display_name = (payload.display_name or "Operator").strip() or "Operator"
    if any(normalize_email(u["email"]) == email for u in users["users"]):
        raise HTTPException(status_code=409, detail="Email already registered")
    operator_id = f"operator_{uuid.uuid4().hex[:8].upper()}"
    user = {"email": email, "password": payload.password, "display_name": display_name, "operator_id": operator_id}
    users["users"].append(user)
    save_users(users)
    ensure_state_for_user(user)
    save_session({"email": email, "operator_id": operator_id, "display_name": display_name, "logged_in": True})
    append_governance_event(email, operator_id, "register", operator_id, {"display_name": display_name}, "auth")
    return {"status": "registered", "operator_id": operator_id, "display_name": display_name, "is_admin": user_is_admin_email(email)}


@app.post("/auth/login")
def auth_login(payload: LoginRequest):
    users = users_db()
    email = normalize_email(payload.email)
    user = next((u for u in users["users"] if normalize_email(u["email"]) == email and u["password"] == payload.password), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    ensure_state_for_user(user)
    save_session({"email": user["email"], "operator_id": user["operator_id"], "display_name": user["display_name"], "logged_in": True})
    append_governance_event(user["email"], user["operator_id"], "login", user["operator_id"], {}, "auth")
    return {"status": "logged_in", "operator_id": user["operator_id"], "display_name": user["display_name"], "is_admin": user_is_admin_email(user["email"])}


@app.post("/auth/logout")
def auth_logout():
    session = get_session()
    if session.get("logged_in"):
        append_governance_event(session.get("email"), session.get("operator_id"), "logout", session.get("operator_id"), {}, "auth")
    save_session(empty_session())
    return {"status": "logged_out"}


@app.get("/auth/me")
def auth_me():
    session = get_session()
    session_payload = session_view(session)
    if session_payload.get("logged_in"):
        try:
            session_payload = resolve_operator_context(session_payload)
        except HTTPException:
            pass
    return session_view(session_payload)


@app.post("/strategies/register")
def strategies_register(payload: StrategyRegisterRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = {
        "strategy_id": f"strat_{uuid.uuid4().hex[:8]}",
        "name": payload.name,
        "symbol": payload.symbol.upper(),
        "side": payload.side.lower(),
        "default_qty": payload.default_qty,
        "enabled": payload.enabled,
        "status": "running" if payload.enabled else "stopped",
        "capital_limit": payload.capital_limit,
        "execution_mode": payload.execution_mode.lower(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "operator_id": session.get("operator_id"),
        "last_action": "register",
        "deleted": False,
    }
    state["strategies"]["strategies"].append(strategy)
    state.setdefault("strategy_engine", {}).setdefault("metrics", {})[strategy["strategy_id"]] = default_strategy_metrics(strategy["strategy_id"], strategy["symbol"])
    strategy_log(state, strategy["strategy_id"], "lifecycle", f"{strategy['name']} registered", strategy)
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "strategy.register", strategy["strategy_id"], strategy, "strategy")
    return {"status": "registered", "strategy": strategy}


@app.get("/strategies/list")
def strategies_list(session=Depends(require_auth)):
    state = get_operator_state(session)
    return summarize_strategy_engine(state)


@app.post("/strategies/toggle")
def strategies_toggle(payload: StrategyToggleRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = get_strategy_by_id(state, payload.strategy_id)
    strategy["enabled"] = payload.enabled
    strategy["updated_at"] = now_iso()
    strategy["last_action"] = "toggle"
    if not payload.enabled:
        strategy["status"] = "stopped"
    strategy_log(state, strategy["strategy_id"], "lifecycle", f"{strategy['name']} enabled={payload.enabled}", {"enabled": payload.enabled})
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "strategy.toggle", strategy["strategy_id"], strategy, "strategy")
    return {"status": "updated", "strategy": strategy}


@app.post("/strategies/lifecycle")
def strategies_lifecycle(payload: StrategyLifecycleRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = get_strategy_by_id(state, payload.strategy_id)
    action = payload.action.lower()
    if action == "start":
        strategy["enabled"] = True
        strategy["status"] = "running"
    elif action == "stop":
        strategy["status"] = "stopped"
    elif action == "pause":
        strategy["status"] = "paused"
    else:
        raise HTTPException(status_code=400, detail="Unsupported lifecycle action")
    strategy["updated_at"] = now_iso()
    strategy["last_action"] = action
    strategy_log(state, strategy["strategy_id"], "lifecycle", f"{strategy['name']} {action}", {"action": action})
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), f"strategy.{action}", strategy["strategy_id"], strategy, "strategy")
    return {"status": action, "strategy": strategy}


@app.post("/strategies/delete")
def strategies_delete(payload: StrategyDeleteRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = get_strategy_by_id(state, payload.strategy_id)
    strategy["deleted"] = True
    strategy["enabled"] = False
    strategy["status"] = "deleted"
    strategy["updated_at"] = now_iso()
    strategy["last_action"] = "delete"
    strategy_log(state, strategy["strategy_id"], "lifecycle", f"{strategy['name']} deleted", {})
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "strategy.delete", strategy["strategy_id"], strategy, "strategy")
    return {"status": "deleted", "strategy_id": strategy["strategy_id"]}


@app.get("/strategies/performance")
def strategies_performance(session=Depends(require_auth)):
    state = get_operator_state(session)
    evaluate_monitoring(state)
    save_operator_state(state)
    return summarize_strategy_engine(state)


@app.get("/strategies/logs")
def strategies_logs(session=Depends(require_auth)):
    state = get_operator_state(session)
    engine = summarize_strategy_engine(state)
    return {"logs": engine["recent_logs"]}


@app.get("/performance/metrics")
def performance_metrics(session=Depends(require_auth)):
    state = get_operator_state(session)
    snapshot = build_performance_snapshot(state)
    save_operator_state(state)
    return snapshot


@app.get("/performance/operator/{operator_id}")
def performance_operator(operator_id: str, session=Depends(require_auth)):
    session_payload = session_view(session)
    if operator_id != session_payload.get("operator_id") and not session_payload.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    state = get_operator_state_by_id(operator_id)
    snapshot = build_performance_snapshot(state)
    save_operator_state(state)
    return snapshot


@app.get("/performance/strategy/{strategy_id}")
def performance_strategy(strategy_id: str, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = get_strategy_by_id(state, strategy_id)
    engine = summarize_strategy_engine(state)
    row = next((s for s in engine.get("strategies", []) if s.get("strategy_id") == strategy_id), None)
    if not row:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"strategy": row, "performance": build_performance_snapshot(state).get("summary", {}), "recent_logs": [l for l in state.get("strategy_engine", {}).get("logs", []) if l.get("strategy_id") == strategy_id][:25]}


@app.post("/allocator/operator-capital/set")
def allocator_operator_capital_set(payload: OperatorCapitalRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    state["allocator_caps"]["operator"] = {
        "operator_id": state["operator_id"],
        "allocated_capital": payload.allocated_capital,
        "status": "FUNDED" if payload.allocated_capital > 0 else "UNFUNDED",
        "updated_at": now_iso(),
    }
    evaluate_monitoring(state)
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "allocator.operator_capital.set", state["operator_id"], state["allocator_caps"]["operator"], "capital")
    return {"status": "set", "operator_capital": state["allocator_caps"]["operator"]}


@app.get("/allocator/capital-view")
def allocator_capital_view(session=Depends(require_auth)):
    state = get_operator_state(session)
    monitoring = evaluate_monitoring(state)
    save_operator_state(state)
    alloc = state["allocator_caps"]["operator"]
    return {"operator": {**alloc, "used_capital": monitoring["latest_snapshot"].get("used_capital", 0), "remaining_capital": monitoring["latest_snapshot"].get("remaining_capital", 0)}}


@app.get("/monitoring/status")
def monitoring_status(session=Depends(require_auth)):
    state = get_operator_state(session)
    result = evaluate_monitoring(state)
    save_operator_state(state)
    return result


@app.get("/orders/list")
def orders_list(session=Depends(require_auth)):
    return get_operator_state(session)["orders"]


@app.post("/orders/submit")
def orders_submit(payload: ManualOrderRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    execution_mode = (payload.execution_mode or "internal").lower()
    symbol = payload.symbol.upper()
    side = payload.side.lower()
    notional = round(get_price(symbol) * float(payload.qty), 2)
    enforce_risk_guard(state, symbol, side, float(payload.qty), execution_mode)
    enforce_capital_guard(state, notional, side)
    if execution_mode == "alpaca":
        if not resolved_alpaca_credentials():
            raise HTTPException(status_code=400, detail="Alpaca mode requested but no Alpaca credentials are configured")
        broker_order = alpaca_submit_market_order(symbol, side, payload.qty)
        order = normalize_alpaca_order(broker_order, symbol, side, payload.qty)
    else:
        order = build_internal_order(symbol, side, payload.qty, execution_mode)
    persist_order(state, order)
    evaluate_monitoring(state)
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "orders.submit", state["operator_id"], order, "execution")
    return {"status": "submitted", "order": order}


@app.post("/operator/run-once")
def operator_run_once(payload: RunOperatorRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    orders = run_strategies_for_state(state, payload.execution_mode, session.get("email"), session.get("operator_id"), "operator.run_once")
    return {"status": "executed", "orders_created": len(orders), "orders": orders}


@app.get("/operator/workspace")
def operator_workspace(session=Depends(require_auth)):
    state = get_operator_state(session)
    return build_operator_workspace(state)


@app.get("/command-center/snapshot")
def command_center_snapshot(session=Depends(require_auth)):
    return build_command_center_snapshot(session)


@app.get("/capital-source/status")
def capital_source_status(session=Depends(require_auth)):
    state = get_operator_state(session)
    capital = build_capital_context(state)
    risk = evaluate_risk_state(state)
    save_operator_state(state)
    return {
        "config": state.get("capital_source", default_capital_source()),
        "context": capital,
        "risk_state": risk.get("status"),
    }


@app.post("/capital-source/update")
def capital_source_update(payload: CapitalSourceUpdateRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    mode = (payload.mode or "internal").strip().lower()
    if mode not in {"internal", "broker"}:
        raise HTTPException(status_code=400, detail="Capital source mode must be internal or broker")
    state["capital_source"] = {
        "mode": mode,
        "provider": "alpaca",
        "last_updated_at": now_iso(),
        "last_updated_by": session.get("email"),
    }
    monitoring = evaluate_monitoring(state)
    risk = evaluate_risk_state(state)
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "capital_source.update", state["operator_id"], state["capital_source"], "capital")
    return {"status": "updated", "capital_source": state["capital_source"], "monitoring": monitoring, "risk_engine": risk}


@app.get("/risk-engine/status")
def risk_engine_status(session=Depends(require_auth)):
    state = get_operator_state(session)
    result = evaluate_risk_state(state)
    save_operator_state(state)
    return result


@app.post("/risk-engine/config/update")
def risk_engine_config_update(payload: RiskConfigUpdateRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    state["risk_engine"].update(payload.model_dump())
    result = evaluate_risk_state(state)
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "risk.config.update", state["operator_id"], payload.model_dump(), "risk")
    return {"status": "updated", "risk_engine": result}


@app.post("/risk-engine/kill-switch")
def risk_engine_kill_switch(payload: RiskKillSwitchRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    state["risk_engine"]["kill_switch_active"] = bool(payload.active)
    if payload.active:
        state["strategy_loop"]["running"] = False
        state["strategy_loop"]["next_run_at"] = None
    result = evaluate_risk_state(state)
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "risk.kill_switch", state["operator_id"], {"active": payload.active, "note": payload.note}, "risk")
    return {"status": "updated", "risk_engine": result}


# -------------------------
# Alpaca routes
# -------------------------
@app.get("/broker/alpaca/status")
def broker_alpaca_status(session=Depends(require_auth)):
    return refresh_alpaca_state(soft=True)


@app.post("/broker/alpaca/connect")
def broker_alpaca_connect(payload: AlpacaConnectRequest, admin=Depends(require_admin)):
    cfg = get_broker_config()
    cfg["alpaca"].update(
        {
            "api_key": payload.api_key.strip(),
            "secret_key": payload.secret_key.strip(),
            "base_url": payload.base_url.strip().rstrip("/"),
            "paper": payload.paper,
            "last_status": "connecting",
            "last_error": None,
        }
    )
    save_broker_config(cfg)
    result = refresh_alpaca_state(soft=False)
    append_governance_event(admin.get("email"), admin.get("operator_id"), "broker.alpaca.connect", "alpaca", {"base_url": payload.base_url, "paper": payload.paper}, "broker")
    return {"status": "connected", "broker": result}


@app.post("/broker/alpaca/disconnect")
def broker_alpaca_disconnect(admin=Depends(require_admin)):
    cfg = get_broker_config()
    cfg["alpaca"] = default_broker_config()["alpaca"]
    save_broker_config(cfg)
    append_governance_event(admin.get("email"), admin.get("operator_id"), "broker.alpaca.disconnect", "alpaca", {}, "broker")
    return {"status": "disconnected", "broker": safe_broker_view(cfg)["alpaca"]}


@app.get("/broker/alpaca/account")
def broker_alpaca_account(session=Depends(require_auth)):
    return {"account": refresh_alpaca_state(soft=True).get("account", {})}


@app.get("/broker/alpaca/positions")
def broker_alpaca_positions(session=Depends(require_auth)):
    return {"positions": refresh_alpaca_state(soft=True).get("positions", [])}


@app.get("/broker/alpaca/orders")
def broker_alpaca_orders(session=Depends(require_auth)):
    return {"orders": refresh_alpaca_state(soft=True).get("orders", [])}


# -------------------------
# Admin + governance routes
# -------------------------
@app.get("/admin/control-tower")
def admin_control_tower(admin=Depends(require_admin)):
    return control_tower_view()


@app.get("/admin/operators")
def admin_operators(admin=Depends(require_admin)):
    return {"operators": control_tower_view()["operators"]}


@app.post("/admin/operator-capital/set")
def admin_operator_capital_set(payload: AdminOperatorCapitalRequest, admin=Depends(require_admin)):
    policy = policy_for("capital_change")
    if policy and abs(float(payload.allocated_capital)) >= float(policy["threshold"]):
        req = submit_approval_request(admin, "capital_change", payload.operator_id, payload.model_dump(), f"Capital change exceeds threshold {policy['threshold']}")
        return {"status": "approval_required", "request": req}
    state = get_operator_state_by_id(payload.operator_id)
    state["allocator_caps"]["operator"] = {
        "operator_id": payload.operator_id,
        "allocated_capital": payload.allocated_capital,
        "status": "FUNDED" if payload.allocated_capital > 0 else "UNFUNDED",
        "updated_at": now_iso(),
    }
    evaluate_monitoring(state)
    save_operator_state(state)
    append_governance_event(admin.get("email"), admin.get("operator_id"), "admin.operator_capital.set", payload.operator_id, state["allocator_caps"]["operator"], "admin")
    return {"status": "set", "operator_id": payload.operator_id, "operator_capital": state["allocator_caps"]["operator"]}


@app.post("/admin/operator-loop/start")
def admin_operator_loop_start(payload: AdminLoopRequest, admin=Depends(require_admin)):
    policy = policy_for("loop_start")
    if policy and int(payload.interval_seconds) < int(policy["threshold"]):
        req = submit_approval_request(admin, "loop_start", payload.operator_id, payload.model_dump(), f"Loop start interval below policy threshold {policy['threshold']}")
        return {"status": "approval_required", "request": req}
    state = get_operator_state_by_id(payload.operator_id)
    state["strategy_loop"]["running"] = True
    state["strategy_loop"]["execution_mode"] = payload.execution_mode
    state["strategy_loop"]["interval_seconds"] = max(5, int(payload.interval_seconds))
    state["strategy_loop"]["heartbeat_at"] = now_iso()
    state["strategy_loop"]["next_run_at"] = (now_dt() + datetime.timedelta(seconds=state["strategy_loop"]["interval_seconds"])).isoformat() + "Z"
    save_operator_state(state)
    append_governance_event(admin.get("email"), admin.get("operator_id"), "admin.operator_loop.start", payload.operator_id, {"execution_mode": payload.execution_mode, "interval_seconds": payload.interval_seconds}, "admin")
    return {"status": "started", "operator_id": payload.operator_id, "loop": state["strategy_loop"]}


@app.post("/admin/run-all-once")
def admin_run_all_once(admin=Depends(require_admin)):
    policy = policy_for("run_all")
    if policy and int(policy["threshold"]) <= 1:
        req = submit_approval_request(admin, "run_all", "fleet", {"scope": "all"}, "Fleet run-all requires approval")
        return {"status": "approval_required", "request": req}
    for user in users_db()["users"]:
        state = get_operator_state_by_id(user["operator_id"])
        run_strategies_for_state(state, state["strategy_loop"].get("execution_mode", "internal"), admin.get("email"), admin.get("operator_id"), "admin.run_all.execute")
    append_governance_event(admin.get("email"), admin.get("operator_id"), "admin.run_all_once", "fleet", {"mode": "direct"}, "admin")
    return {"status": "ran_all_once_direct"}


@app.get("/governance/ledger")
def governance_ledger(admin=Depends(require_admin)):
    return load_json("governance_ledger.json", {"events": []})


@app.get("/governance/ledger/summary")
def governance_ledger_summary(admin=Depends(require_admin)):
    ledger = load_json("governance_ledger.json", {"events": []})["events"]
    return summarize_governance(ledger)


@app.get("/policy-engine/policies")
def policy_engine_policies(admin=Depends(require_admin)):
    return get_policies()


@app.post("/policy-engine/policies/update")
def policy_engine_policies_update(payload: PolicyUpdateRequest, admin=Depends(require_admin)):
    data = get_policies()
    found = None
    for policy in data["policies"]:
        if policy["policy_id"] == payload.policy_id:
            policy["threshold"] = payload.threshold
            policy["enabled"] = payload.enabled
            found = policy
            break
    if not found:
        raise HTTPException(status_code=404, detail="Policy not found")
    save_policies(data)
    append_governance_event(admin.get("email"), admin.get("operator_id"), "policy.update", payload.policy_id, found, "policy")
    return {"status": "updated", "policy": found}


@app.get("/approvals/queue")
def approvals_queue(admin=Depends(require_admin)):
    return get_approvals()


@app.post("/approvals/decision")
def approvals_decision(payload: ApprovalDecisionRequest, admin=Depends(require_admin)):
    queue = get_approvals()
    req = next((r for r in queue["requests"] if r["request_id"] == payload.request_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if req["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Approval request already decided")
    req["status"] = payload.decision.upper()
    req["reviewed_at"] = now_iso()
    req["reviewed_by"] = admin.get("email")
    req["notes"] = payload.notes
    if req["status"] == "APPROVED":
        apply_approval_request(req, admin)
    else:
        append_governance_event(admin.get("email"), admin.get("operator_id"), "approval.rejected", req["target"], req, "approval")
    save_approvals(queue)
    return {"status": req["status"], "request": req}


@app.get("/version")
def version():
    return {
        "mission": "QNT30324C Broker Capital Metrics Normalization",
        "layer": "qnt30324c-broker-capital-metrics-normalization",
        "frontend": "qnt30324c",
        "cache_policy": NO_CACHE_HEADERS["Cache-Control"],
        "timestamp": now_iso(),
    }


@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index, media_type="text/html", headers=NO_CACHE_HEADERS)
    return {"status": "ok", "message": "Quantora QNT30324B live"}


@app.get("/{page_name}")
def static_pages(page_name: str):
    page = FRONTEND_DIR / page_name
    if page.suffix == "" and not page_name.endswith(".html"):
        page = FRONTEND_DIR / f"{page_name}.html"
    if page.exists() and page.is_file():
        return FileResponse(page, headers=NO_CACHE_HEADERS if page.suffix == ".html" else None)
    return JSONResponse({"error": "not found", "page": page_name}, status_code=404)
