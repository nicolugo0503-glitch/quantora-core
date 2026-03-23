import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
FRONTEND_DIR = PROJECT_DIR / "frontend"

app = FastAPI(title="Quantora QNT30323 Real Strategy Engine", version="30323")
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


# -------------------------
# Generic utilities
# -------------------------
def now_dt():
    return datetime.datetime.utcnow().replace(microsecond=0)


def now_iso():
    return now_dt().isoformat() + "Z"


def load_json(filename, fallback):
    path = ARTIFACTS_DIR / filename
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def save_json(filename, data):
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")


def users_db():
    return load_json("users.json", {"users": []})


def save_users(data):
    save_json("users.json", data)


def get_session():
    return load_json("session.json", {"logged_in": False, "display_name": None, "operator_id": None, "email": None})


def save_session(data):
    save_json("session.json", data)


def get_policies():
    return load_json("policy_engine.json", {"policies": []})


def save_policies(data):
    save_json("policy_engine.json", data)


def get_approvals():
    return load_json("approval_queue.json", {"requests": []})


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
    if session.get("email") not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return session


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


def migrate_operator_state(state, display_name=None):
    state.setdefault("display_name", display_name or state.get("display_name") or "Operator")
    state.setdefault("strategies", {"strategies": []})
    state.setdefault("orders", {"orders": []})
    state.setdefault("allocator_caps", {"operator": {"operator_id": state.get("operator_id"), "allocated_capital": 0.0, "status": "UNFUNDED", "updated_at": None}})
    state.setdefault("strategy_loop", {"running": False, "execution_mode": "internal", "interval_seconds": 60, "last_run_at": None, "next_run_at": None, "heartbeat_at": None, "total_runs": 0, "total_signals": 0, "total_orders": 0})
    state.setdefault("monitoring", {"latest_snapshot": {}, "alerts": [], "last_evaluated_at": None})
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
        existing = migrate_operator_state(existing, user.get("display_name"))
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
    state = migrate_operator_state(state, user.get("display_name"))
    save_operator_state(state)
    return state


def get_operator_state(session):
    return get_operator_state_by_id(session.get("operator_id"))


def save_operator_state(state):
    save_json(state_filename(state["operator_id"]), state)


def policy_for(policy_type):
    for policy in get_policies()["policies"]:
        if policy["policy_type"] == policy_type and policy.get("enabled"):
            return policy
    return None


def available_operator_capital(state):
    exposure = operator_exposure(state)
    allocated = float(state["allocator_caps"]["operator"].get("allocated_capital", 0) or 0)
    return round(allocated - exposure["notional"], 2)


def enforce_capital_guard(state, notional, side, strategy=None):
    if (side or "buy").lower() != "buy":
        return
    remaining = available_operator_capital(state)
    allocated = float(state["allocator_caps"]["operator"].get("allocated_capital", 0) or 0)
    if allocated <= 0:
        strategy_id = strategy.get("strategy_id") if strategy else None
        if strategy_id:
            strategy_log(state, strategy_id, "risk_block", "Buy order blocked: operator has no allocated capital", {"required": notional, "remaining": remaining})
        raise HTTPException(status_code=400, detail="Capital guard: operator has no allocated capital")
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


def evaluate_monitoring(state):
    exposure = operator_exposure(state)
    allocated = float(state["allocator_caps"]["operator"].get("allocated_capital", 0) or 0)
    utilization = round((exposure["notional"] / allocated) * 100, 2) if allocated > 0 else 0.0
    alerts = []
    if exposure["notional"] > allocated and allocated >= 0:
        alerts.append({"level": "critical", "type": "capital-breach", "message": f"Open exposure {exposure['notional']} exceeds allocated capital {allocated}"})
    elif utilization >= 80 and allocated > 0:
        alerts.append({"level": "warn", "type": "operator-utilization", "message": f"Operator utilization at {utilization}%"})
    if state["strategy_loop"].get("running") and not state["strategy_loop"].get("heartbeat_at"):
        alerts.append({"level": "warn", "type": "loop-heartbeat", "message": "Loop is marked running without heartbeat"})

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
        "order_count": exposure["orders"],
        "used_capital": exposure["notional"],
        "allocated_capital": allocated,
        "remaining_capital": round(allocated - exposure["notional"], 2),
        "utilization_pct": utilization,
        "alerts_count": len(alerts),
        "strategy_realized_pnl": totals["portfolio_realized_pnl"],
        "strategy_unrealized_pnl": totals["portfolio_unrealized_pnl"],
        "active_strategies": totals["running_strategies"],
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

    for strategy in strategies:
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
    save_operator_state(state)
    orders = state["orders"]["orders"][:12]
    return {
        "operator_id": state["operator_id"],
        "display_name": state["display_name"],
        "capital": {
            **state["allocator_caps"]["operator"],
            "used_capital": monitoring["latest_snapshot"].get("used_capital", 0),
            "remaining_capital": monitoring["latest_snapshot"].get("remaining_capital", 0),
            "utilization_pct": monitoring["latest_snapshot"].get("utilization_pct", 0),
        },
        "strategies": engine,
        "strategy_loop": state["strategy_loop"],
        "orders": orders,
        "positions": operator_positions_from_orders(state)[0],
        "monitoring": monitoring,
        "execution_summary": {
            "recent_orders": len(orders),
            "enabled_strategies": engine["enabled_strategies"],
            "running_strategies": engine["running_strategies"],
            "total_orders": state["strategy_loop"].get("total_orders", 0),
            "realized_pnl": engine["portfolio_realized_pnl"],
            "unrealized_pnl": engine["portfolio_unrealized_pnl"],
        },
    }


def build_command_center_snapshot(session):
    users = users_db()["users"]
    state = get_operator_state(session)
    workspace = build_operator_workspace(state)
    approvals = get_approvals()["requests"]
    ledger = load_json("governance_ledger.json", {"events": []})["events"]
    pending = [r for r in approvals if r.get("status") == "PENDING"]
    broker = refresh_alpaca_state(soft=True)
    snapshot = {
        "session": {**session, "is_admin": session.get("email") in ADMIN_EMAILS},
        "north_star": {
            "mission": "QNT30323 Real Strategy Engine",
            "system": "Quantora multi-layer institutional trading operating system",
            "timestamp": now_iso(),
        },
        "personal_workspace": workspace,
        "strategy_engine": workspace["strategies"],
        "broker": broker,
        "governance": {
            "pending_approvals": len(pending),
            "approvals": approvals[:8],
            "policies": get_policies()["policies"],
            "ledger_summary": summarize_governance(ledger),
            "recent_events": ledger[:8],
        },
        "system_health": {
            "status": "ok",
            "registered_users": len(users),
            "policies_enabled": len([p for p in get_policies()["policies"] if p.get("enabled")]),
            "layer": "qnt30323-real-strategy-engine",
            "broker_status": broker.get("last_status"),
        },
    }
    if session.get("email") in ADMIN_EMAILS:
        snapshot["control_tower"] = control_tower_view()
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
        state = migrate_operator_state(state, user.get("display_name"))
        monitoring = evaluate_monitoring(state)
        engine = summarize_strategy_engine(state)
        save_operator_state(state)
        allocated = float(state["allocator_caps"]["operator"].get("allocated_capital", 0) or 0)
        row = {
            "operator_id": user["operator_id"],
            "display_name": user["display_name"],
            "email": user["email"],
            "orders": len(state["orders"]["orders"]),
            "strategies": engine["total_strategies"],
            "allocated_capital": allocated,
            "used_capital": monitoring["latest_snapshot"].get("used_capital", 0),
            "remaining_capital": round(allocated - monitoring["latest_snapshot"].get("used_capital", 0), 2),
            "loop_running": state["strategy_loop"]["running"],
            "alerts": len(monitoring["alerts"]),
            "execution_mode": state["strategy_loop"].get("execution_mode"),
            "last_run_at": state["strategy_loop"].get("last_run_at"),
            "realized_pnl": engine["portfolio_realized_pnl"],
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
            state = migrate_operator_state(state, user.get("display_name"))
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


class ManualOrderRequest(BaseModel):
    symbol: str
    side: str
    qty: float
    execution_mode: str = "internal"


# -------------------------
# Core routes
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok", "layer": "qnt30323-real-strategy-engine"}


@app.post("/auth/register")
def auth_register(payload: RegisterRequest):
    users = users_db()
    if any(u["email"].lower() == payload.email.lower() for u in users["users"]):
        raise HTTPException(status_code=400, detail="Email already registered")
    operator_id = f"operator_{uuid.uuid4().hex[:8].upper()}"
    user = {"email": payload.email, "password": payload.password, "display_name": payload.display_name, "operator_id": operator_id}
    users["users"].append(user)
    save_users(users)
    ensure_state_for_user(user)
    save_session({"email": payload.email, "operator_id": operator_id, "display_name": payload.display_name, "logged_in": True})
    append_governance_event(payload.email, operator_id, "register", operator_id, {"display_name": payload.display_name}, "auth")
    return {"status": "registered", "operator_id": operator_id, "display_name": payload.display_name, "is_admin": payload.email in ADMIN_EMAILS}


@app.post("/auth/login")
def auth_login(payload: LoginRequest):
    users = users_db()
    user = next((u for u in users["users"] if u["email"].lower() == payload.email.lower() and u["password"] == payload.password), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    ensure_state_for_user(user)
    save_session({"email": user["email"], "operator_id": user["operator_id"], "display_name": user["display_name"], "logged_in": True})
    append_governance_event(user["email"], user["operator_id"], "login", user["operator_id"], {}, "auth")
    return {"status": "logged_in", "operator_id": user["operator_id"], "display_name": user["display_name"], "is_admin": user["email"] in ADMIN_EMAILS}


@app.post("/auth/logout")
def auth_logout():
    session = get_session()
    if session.get("logged_in"):
        append_governance_event(session.get("email"), session.get("operator_id"), "logout", session.get("operator_id"), {}, "auth")
    save_session({"logged_in": False, "display_name": None, "operator_id": None, "email": None})
    return {"status": "logged_out"}


@app.get("/auth/me")
def auth_me():
    session = get_session()
    return {**session, "is_admin": session.get("email") in ADMIN_EMAILS if session.get("email") else False}


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
        "mission": "QNT30323 Real Strategy Engine",
        "layer": "qnt30323-real-strategy-engine",
        "frontend": "qnt30323",
        "cache_policy": NO_CACHE_HEADERS["Cache-Control"],
        "timestamp": now_iso(),
    }


@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index, media_type="text/html", headers=NO_CACHE_HEADERS)
    return {"status": "ok", "message": "Quantora QNT30323 live"}


@app.get("/{page_name}")
def static_pages(page_name: str):
    page = FRONTEND_DIR / page_name
    if page.suffix == "" and not page_name.endswith(".html"):
        page = FRONTEND_DIR / f"{page_name}.html"
    if page.exists() and page.is_file():
        return FileResponse(page)
    return JSONResponse({"error": "not found", "page": page_name}, status_code=404)
