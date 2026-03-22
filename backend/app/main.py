import os, json, uuid, datetime, requests
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
FRONTEND_DIR = PROJECT_DIR / "frontend"

app = FastAPI(title="Quantora QNT30311", version="30311")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(filename: str, fallback):
    p = ARTIFACTS_DIR / filename
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else fallback

def save_json(filename: str, data):
    (ARTIFACTS_DIR / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")

def users_db():
    return load_json("users.json", {"users": []})

def save_users(data):
    save_json("users.json", data)

def get_session():
    return load_json("session.json", {"logged_in": False, "display_name": None, "operator_id": None, "email": None})

def save_session(data):
    save_json("session.json", data)

def require_auth():
    s = get_session()
    if not s.get("logged_in"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return s

def state_filename(operator_id: str):
    return f"operator_state_{operator_id}.json"

def reports_filename(operator_id: str):
    return f"operator_reports_{operator_id}.json"

def first_nonempty(*names):
    for n in names:
        v = os.getenv(n)
        if v and str(v).strip():
            return str(v).strip()
    return None

def alpaca_key():
    return first_nonempty("ALPACA_API_KEY", "APCA_API_KEY_ID", "ALPACA_KEY")

def alpaca_secret():
    return first_nonempty("ALPACA_SECRET_KEY", "APCA_API_SECRET_KEY", "ALPACA_SECRET")

def alpaca_base_url():
    return (first_nonempty("ALPACA_BASE_URL") or "https://paper-api.alpaca.markets").rstrip("/")

def alpaca_headers():
    return {
        "APCA-API-KEY-ID": alpaca_key() or "",
        "APCA-API-SECRET-KEY": alpaca_secret() or "",
        "Content-Type": "application/json",
    }

def get_price(symbol: str):
    prices = {"AAPL": 180.0, "TSLA": 175.0, "SPY": 510.0, "NVDA": 910.0, "MSFT": 420.0}
    return prices.get(symbol.upper(), 100.0)

def default_operator_state(operator_id: str, display_name: str):
    trust_score = 82
    risk_score = 79
    allocated = int(max(0, trust_score * 250) * max(0.4, min(1.0, risk_score / 100.0)))
    return {
        "operator_id": operator_id,
        "display_name": display_name,
        "passport": {
            "operator_id": operator_id,
            "passport_status": "ACTIVE",
            "deployment_stage": "STAGE_2_MICRO_LIVE",
            "score_last_updated": now_iso(),
            "discipline_score": 84,
            "risk_score": 79,
            "consistency_score": 81,
            "trust_score": trust_score,
            "violation_count": 0,
            "audit_status": "VALID",
        },
        "score": {
            "trust_score": trust_score,
            "discipline_score": 84,
            "risk_score": 79,
            "consistency_score": 81,
            "performance_score": 80,
            "audit_integrity_score": 100,
        },
        "violations": {"operator_id": operator_id, "violation_count": 0, "critical_violation_count": 0, "violations": []},
        "capital_decision": {
            "approved": True,
            "capital_allocated": allocated,
            "confidence": 0.82,
            "reason": "Capital engine evaluation complete",
            "inputs": {"trust_score": trust_score, "risk_score": risk_score, "violation_count": 0, "critical_violation_count": 0},
        },
        "broker_status": {"broker": "alpaca-paper", "mode": "paper", "connected": False, "provider": "alpaca", "last_sync": None},
        "portfolio": {"equity": 25000.0, "cash": 19000.0, "buying_power": float(allocated), "positions_count": 0, "unrealized_pl": 0.0},
        "orders": {"orders": []},
        "positions": {"positions": []},
        "strategies": {"strategies": []},
        "signals": {"signals": []},
        "runtime": {"active_strategies": 0, "last_signal": None, "last_execution": None},
        "blocked_orders": {"blocked_orders": []},
        "blocked_signals": {"blocked_signals": []},
        "enforcement": {"status": "READY", "last_check": None, "last_decision": None},
        "allocator": {"operator_id": operator_id, "requested_capital": 0.0, "deployed_capital": 0.0, "status": "NOT_DEPLOYED", "latest_allocation_id": None},
        "broker_sync": {
            "account_summary": {},
            "synced_positions": [],
            "synced_orders": [],
            "synced_fills": [],
            "pnl": {"equity": 0.0, "cash": 0.0, "long_market_value": 0.0, "short_market_value": 0.0, "unrealized_pl": 0.0, "unrealized_plpc": 0.0},
            "last_synced_at": None,
            "reconciliation": {"order_gap": 0, "position_gap": 0, "notes": []}
        },
        "audit": {"status": "VALID", "checked_files": 26, "failed_files": [], "details": {"qnt30311": "OK"}, "timestamp": now_iso()},
    }

def default_reports(operator_id: str, display_name: str):
    return {
        "operator_id": operator_id,
        "display_name": display_name,
        "execution_ledger": {"entries": []},
        "fills": {"fills": []},
        "strategy_execution_history": {"events": []},
        "performance": {
            "as_of": now_iso(),
            "orders_count": 0,
            "fills_count": 0,
            "gross_notional": 0.0,
            "realized_pl": 0.0,
            "unrealized_pl": 0.0,
            "equity": 25000.0,
            "cash": 19000.0,
        },
        "evidence_packet": {
            "packet_id": f"evidence_{operator_id}",
            "operator_id": operator_id,
            "generated_at": now_iso(),
            "summary": {"orders_count": 0, "fills_count": 0, "strategies_count": 0, "equity": 25000.0, "cash": 19000.0},
            "artifacts": ["execution_ledger", "fills", "strategy_execution_history", "performance"],
        },
    }

def ensure_state_for_user(user):
    operator_id = user["operator_id"]
    if load_json(state_filename(operator_id), None) is None:
        save_json(state_filename(operator_id), default_operator_state(operator_id, user["display_name"]))
    if load_json(reports_filename(operator_id), None) is None:
        save_json(reports_filename(operator_id), default_reports(operator_id, user["display_name"]))

def get_operator_state(session):
    operator_id = session.get("operator_id")
    users = users_db()
    user = next((u for u in users["users"] if u["operator_id"] == operator_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found")
    ensure_state_for_user(user)
    return load_json(state_filename(operator_id), {})

def save_operator_state(state):
    save_json(state_filename(state["operator_id"]), state)

def get_reports(session):
    state = get_operator_state(session)
    operator_id = state["operator_id"]
    reports = load_json(reports_filename(operator_id), None)
    if reports is None:
        reports = default_reports(operator_id, state["display_name"])
        save_json(reports_filename(operator_id), reports)
    return reports

def save_reports(operator_id, reports):
    save_json(reports_filename(operator_id), reports)

def refresh_reports_from_state(state):
    operator_id = state["operator_id"]
    reports = load_json(reports_filename(operator_id), default_reports(operator_id, state["display_name"]))
    orders = state["orders"]["orders"]
    fills = reports["fills"]["fills"]
    pnl = state.get("broker_sync", {}).get("pnl", {})
    reports["performance"] = {
        "as_of": now_iso(),
        "orders_count": len(orders),
        "fills_count": len(fills),
        "gross_notional": round(sum(float(f.get("notional", 0)) for f in fills), 2),
        "realized_pl": 0.0,
        "unrealized_pl": float(pnl.get("unrealized_pl", state["portfolio"].get("unrealized_pl", 0.0))),
        "equity": float(pnl.get("equity", state["portfolio"].get("equity", 0.0))),
        "cash": float(pnl.get("cash", state["portfolio"].get("cash", 0.0))),
    }
    reports["evidence_packet"] = {
        "packet_id": f"evidence_{operator_id}",
        "operator_id": operator_id,
        "generated_at": now_iso(),
        "summary": {
            "orders_count": len(orders),
            "fills_count": len(fills),
            "strategies_count": len(state["strategies"]["strategies"]),
            "equity": float(pnl.get("equity", state["portfolio"].get("equity", 0.0))),
            "cash": float(pnl.get("cash", state["portfolio"].get("cash", 0.0))),
        },
        "artifacts": ["execution_ledger", "fills", "strategy_execution_history", "performance", "broker_sync"],
    }
    save_reports(operator_id, reports)
    return reports

def record_execution(state, order, fill):
    operator_id = state["operator_id"]
    reports = load_json(reports_filename(operator_id), default_reports(operator_id, state["display_name"]))
    reports["execution_ledger"]["entries"].append({
        "entry_id": f"ledger_{uuid.uuid4().hex[:8]}",
        "timestamp": now_iso(),
        "operator_id": operator_id,
        "order_id": order["order_id"],
        "symbol": order["symbol"],
        "side": order["side"],
        "qty": order["qty"],
        "notional": order["notional"],
        "strategy_id": order.get("strategy_id"),
        "broker_mode": order.get("broker_mode", "internal-paper"),
    })
    reports["fills"]["fills"].append(fill)
    if order.get("strategy_id"):
        reports["strategy_execution_history"]["events"].append({
            "event_id": f"strex_{uuid.uuid4().hex[:8]}",
            "timestamp": now_iso(),
            "strategy_id": order.get("strategy_id"),
            "order_id": order["order_id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "qty": order["qty"],
            "status": order["status"],
        })
    save_reports(operator_id, reports)
    return refresh_reports_from_state(state)

def security_status_payload():
    return {
        "env_mode": os.getenv("QUANTORA_ENV", "development"),
        "has_alpaca_key": bool(alpaca_key()),
        "has_alpaca_secret": bool(alpaca_secret()),
        "alpaca_base_url": alpaca_base_url(),
        "has_quantora_secret": bool(first_nonempty("QUANTORA_SECRET_KEY")),
    }

def alpaca_status_payload():
    base = alpaca_base_url()
    key = alpaca_key()
    secret = alpaca_secret()
    if not key or not secret:
        return {"connected": False, "error": "Missing Alpaca credentials in runtime environment", "base_url": base}
    try:
        r = requests.get(f"{base}/v2/account", headers=alpaca_headers(), timeout=20)
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        return {"connected": r.status_code == 200, "status_code": r.status_code, "base_url": base, "response": body}
    except Exception as e:
        return {"connected": False, "base_url": base, "error": str(e)}

def enforcement_check(symbol: str, side: str, qty: int, session: dict, source: str = "manual", strategy_id=None):
    state = get_operator_state(session)
    capital = state["capital_decision"]
    score = state["score"]
    violations = state["violations"]
    passport = state["passport"]
    notional = round(get_price(symbol) * qty, 2)
    reasons = []
    allowed = True
    if not session.get("logged_in"):
        allowed = False; reasons.append("Authentication required")
    if not capital.get("approved"):
        allowed = False; reasons.append("Capital decision not approved")
    if score.get("trust_score", 0) < 70:
        allowed = False; reasons.append("Trust score below threshold")
    if violations.get("critical_violation_count", 0) > 0:
        allowed = False; reasons.append("Critical violations present")
    if passport.get("deployment_stage") not in ["STAGE_2_MICRO_LIVE", "STAGE_3_LIMITED_LIVE", "STAGE_4_ALLOCATOR_LIVE", "STAGE_5_SCALED_CAPITAL"]:
        allowed = False; reasons.append("Deployment stage not eligible")
    if notional > float(capital.get("capital_allocated", 0)):
        allowed = False; reasons.append("Order exceeds allocated capital")
    decision = {"allowed": allowed, "symbol": symbol.upper(), "side": side.lower(), "qty": qty, "estimated_notional": notional, "source": source, "strategy_id": strategy_id, "operator_id": session.get("operator_id"), "timestamp": now_iso(), "reasons": reasons if reasons else ["Enforcement passed"]}
    state["enforcement"]["last_check"] = now_iso()
    state["enforcement"]["last_decision"] = decision
    state["enforcement"]["status"] = "ALLOW" if allowed else "BLOCK"
    if not allowed:
        if source == "strategy":
            state["blocked_signals"]["blocked_signals"].append(decision)
        else:
            state["blocked_orders"]["blocked_orders"].append(decision)
    save_operator_state(state)
    return decision

def alpaca_get(path: str, params=None):
    if not alpaca_key() or not alpaca_secret():
        raise HTTPException(status_code=400, detail="Missing Alpaca credentials")
    r = requests.get(f"{alpaca_base_url()}{path}", headers=alpaca_headers(), params=params, timeout=20)
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text[:1000]}
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=data)
    return data

def compute_pnl_from_account(account):
    return {
        "equity": float(account.get("equity", 0) or 0),
        "cash": float(account.get("cash", 0) or 0),
        "long_market_value": float(account.get("long_market_value", 0) or 0),
        "short_market_value": float(account.get("short_market_value", 0) or 0),
        "unrealized_pl": float(account.get("unrealized_pl", 0) or 0),
        "unrealized_plpc": float(account.get("unrealized_plpc", 0) or 0),
    }

def sync_broker_state(session):
    state = get_operator_state(session)
    account = alpaca_get("/v2/account")
    positions = alpaca_get("/v2/positions")
    orders = alpaca_get("/v2/orders", params={"status": "all", "limit": 100})
    activities = alpaca_get("/v2/account/activities/FILL", params={"page_size": 100})
    pnl = compute_pnl_from_account(account)
    synced_positions = [{"symbol": p.get("symbol"), "qty": p.get("qty"), "side": p.get("side"), "market_value": p.get("market_value"), "avg_entry_price": p.get("avg_entry_price"), "unrealized_pl": p.get("unrealized_pl"), "unrealized_plpc": p.get("unrealized_plpc")} for p in positions]
    synced_orders = [{"order_id": o.get("id"), "symbol": o.get("symbol"), "side": o.get("side"), "qty": o.get("qty"), "filled_qty": o.get("filled_qty"), "status": o.get("status"), "type": o.get("type") or o.get("order_type"), "submitted_at": o.get("submitted_at"), "filled_avg_price": o.get("filled_avg_price")} for o in orders]
    synced_fills = [{"activity_id": f.get("id"), "symbol": f.get("symbol"), "side": f.get("side"), "qty": f.get("qty"), "price": f.get("price"), "transaction_time": f.get("transaction_time"), "order_id": f.get("order_id")} for f in activities]
    local_orders = state["orders"]["orders"]
    reconciliation = {"order_gap": max(0, len(synced_orders) - len(local_orders)), "position_gap": abs(len(synced_positions) - len(state["positions"]["positions"])), "notes": []}
    if reconciliation["order_gap"] > 0:
        reconciliation["notes"].append("Broker has more orders than local state.")
    if reconciliation["position_gap"] > 0:
        reconciliation["notes"].append("Broker positions differ from local positions.")
    if not reconciliation["notes"]:
        reconciliation["notes"].append("Broker and operator state are materially aligned.")
    state["broker_status"] = {"broker": "alpaca-paper", "mode": "paper", "connected": True, "provider": "alpaca", "last_sync": now_iso()}
    state["broker_sync"] = {
        "account_summary": {"account_number": account.get("account_number"), "status": account.get("status"), "buying_power": account.get("buying_power"), "equity": account.get("equity"), "cash": account.get("cash"), "portfolio_value": account.get("portfolio_value")},
        "synced_positions": synced_positions,
        "synced_orders": synced_orders,
        "synced_fills": synced_fills,
        "pnl": pnl,
        "last_synced_at": now_iso(),
        "reconciliation": reconciliation,
    }
    state["positions"]["positions"] = [{"symbol": p["symbol"], "qty": float(p["qty"]) if p["qty"] is not None else 0, "avg_price": float(p["avg_entry_price"]) if p["avg_entry_price"] is not None else 0, "market_value": float(p["market_value"]) if p["market_value"] is not None else 0} for p in synced_positions]
    state["portfolio"]["positions_count"] = len(state["positions"]["positions"])
    state["portfolio"]["equity"] = pnl["equity"]
    state["portfolio"]["cash"] = pnl["cash"]
    state["portfolio"]["unrealized_pl"] = pnl["unrealized_pl"]
    state["portfolio"]["buying_power"] = float(account.get("buying_power", 0) or 0)
    save_operator_state(state)
    reports = refresh_reports_from_state(state)
    save_json("latest_broker_sync.json", {"operator_id": state["operator_id"], "synced_at": now_iso(), "broker_sync": state["broker_sync"]})
    return {"status": "synced", "operator_id": state["operator_id"], "broker_sync": state["broker_sync"], "reports": reports["performance"]}

def execute_internal_paper(symbol: str, side: str, qty: int, session, strategy_id=None):
    state = get_operator_state(session)
    fill_price = get_price(symbol)
    notional = round(fill_price * qty, 2)
    portfolio = state["portfolio"]
    positions = state["positions"]
    orders = state["orders"]
    capital = state["capital_decision"]
    order = {"order_id": f"ord_{uuid.uuid4().hex[:10]}", "symbol": symbol.upper(), "side": side.lower(), "qty": qty, "order_type": "market", "status": "filled", "fill_price": fill_price, "notional": notional, "timestamp": now_iso(), "operator_id": session.get("operator_id"), "strategy_id": strategy_id, "broker_mode": "internal-paper"}
    fill = {"fill_id": f"fill_{uuid.uuid4().hex[:10]}", "order_id": order["order_id"], "symbol": order["symbol"], "side": order["side"], "qty": order["qty"], "price": fill_price, "notional": notional, "timestamp": now_iso(), "operator_id": session.get("operator_id")}
    if order["side"] == "buy":
        existing = next((p for p in positions["positions"] if p["symbol"] == order["symbol"]), None)
        if existing:
            existing["qty"] += qty
            existing["market_value"] = round(existing["qty"] * fill_price, 2)
        else:
            positions["positions"].append({"symbol": order["symbol"], "qty": qty, "avg_price": fill_price, "market_value": notional})
        portfolio["cash"] = round(float(portfolio.get("cash", 0)) - notional, 2)
    else:
        existing = next((p for p in positions["positions"] if p["symbol"] == order["symbol"]), None)
        if not existing or existing["qty"] < qty:
            raise HTTPException(status_code=400, detail="Not enough position to sell")
        existing["qty"] -= qty
        portfolio["cash"] = round(float(portfolio.get("cash", 0)) + notional, 2)
        existing["market_value"] = round(existing["qty"] * fill_price, 2)
        if existing["qty"] == 0:
            positions["positions"] = [p for p in positions["positions"] if p["symbol"] != order["symbol"]]
    orders["orders"].append(order)
    portfolio["positions_count"] = len(positions["positions"])
    portfolio["buying_power"] = max(0.0, float(capital.get("capital_allocated", 0)) - sum(float(p.get("market_value", 0)) for p in positions["positions"]))
    portfolio["equity"] = round(float(portfolio["cash"]) + sum(float(p.get("market_value", 0)) for p in positions["positions"]), 2)
    state["runtime"]["last_execution"] = order
    save_operator_state(state)
    reports = record_execution(state, order, fill)
    return {"status": "filled", "mode": "internal-paper", "order": order, "fill": fill, "portfolio": portfolio, "positions": positions, "reports": reports["performance"]}

def place_alpaca_order(symbol: str, side: str, qty: int):
    if not alpaca_key() or not alpaca_secret():
        raise HTTPException(status_code=400, detail="Missing Alpaca credentials")
    body = {"symbol": symbol.upper(), "qty": qty, "side": side.lower(), "type": "market", "time_in_force": "gtc"}
    r = requests.post(f"{alpaca_base_url()}/v2/orders", headers=alpaca_headers(), json=body, timeout=20)
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text[:1000]}
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=data)
    return data

def execute_real_alpaca(symbol: str, side: str, qty: int, session, strategy_id=None):
    state = get_operator_state(session)
    alpaca_order = place_alpaca_order(symbol, side, qty)
    fill_price = float(alpaca_order.get("filled_avg_price") or alpaca_order.get("limit_price") or get_price(symbol))
    notional = round(fill_price * qty, 2)
    order = {"order_id": alpaca_order.get("id", f"alp_{uuid.uuid4().hex[:10]}"), "symbol": symbol.upper(), "side": side.lower(), "qty": qty, "order_type": alpaca_order.get("order_type", alpaca_order.get("type", "market")), "status": alpaca_order.get("status", "submitted"), "fill_price": fill_price, "notional": notional, "timestamp": now_iso(), "operator_id": session.get("operator_id"), "strategy_id": strategy_id, "broker_mode": "alpaca-paper", "broker_payload": alpaca_order}
    fill = {"fill_id": f"fill_{uuid.uuid4().hex[:10]}", "order_id": order["order_id"], "symbol": order["symbol"], "side": order["side"], "qty": order["qty"], "price": fill_price, "notional": notional, "timestamp": now_iso(), "operator_id": session.get("operator_id")}
    state["orders"]["orders"].append(order)
    state["runtime"]["last_execution"] = order
    save_operator_state(state)
    reports = record_execution(state, order, fill)
    return {"status": order["status"], "mode": "alpaca-paper", "order": order, "fill": fill, "reports": reports["performance"]}

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class OrderRequest(BaseModel):
    symbol: str
    side: str
    qty: int
    order_type: str = "market"
    strategy_id: str | None = None
    execution_mode: str = "internal"

class StrategyRegisterRequest(BaseModel):
    name: str
    symbol: str
    side: str
    default_qty: int
    enabled: bool = True

class SignalRequest(BaseModel):
    strategy_id: str
    symbol: str | None = None
    side: str | None = None
    qty: int | None = None
    execution_mode: str = "internal"

class AllocationRequest(BaseModel):
    operator_id: str
    requested_capital: float
    allocator_id: str = "allocator_demo_001"
    mandate_name: str = "default_mandate"

class ApprovalRequest(BaseModel):
    allocation_id: str
    approved_capital: float

@app.get("/health")
def health():
    return {"status": "ok", "service": "quantora-core", "layer": "qnt30311-broker-sync"}

@app.get("/debug/env")
def debug_env():
    return {"ALPACA_API_KEY": bool(os.getenv("ALPACA_API_KEY")), "ALPACA_SECRET_KEY": bool(os.getenv("ALPACA_SECRET_KEY")), "ALPACA_BASE_URL": bool(os.getenv("ALPACA_BASE_URL")), "resolved_key": bool(alpaca_key()), "resolved_secret": bool(alpaca_secret()), "resolved_base_url": alpaca_base_url()}

@app.get("/security/status")
def security_status():
    return {"status": "ok", "security": security_status_payload()}

@app.get("/alpaca/status")
def alpaca_status():
    return alpaca_status_payload()

@app.get("/alpaca/account")
def alpaca_account():
    if not alpaca_key() or not alpaca_secret():
        return JSONResponse({"error": "Missing Alpaca credentials"}, status_code=400)
    r = requests.get(f"{alpaca_base_url()}/v2/account", headers=alpaca_headers(), timeout=20)
    try:
        return JSONResponse(r.json(), status_code=r.status_code)
    except Exception:
        return JSONResponse({"raw": r.text[:1000]}, status_code=r.status_code)

@app.get("/alpaca/orders")
def alpaca_orders():
    return alpaca_get("/v2/orders", params={"status": "all", "limit": 100})

@app.get("/alpaca/positions")
def alpaca_positions():
    return alpaca_get("/v2/positions")

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
    return {"status": "registered", "operator_id": operator_id, "display_name": payload.display_name}

@app.post("/auth/login")
def auth_login(payload: LoginRequest):
    users = users_db()
    user = next((u for u in users["users"] if u["email"].lower() == payload.email.lower() and u["password"] == payload.password), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    ensure_state_for_user(user)
    save_session({"email": user["email"], "operator_id": user["operator_id"], "display_name": user["display_name"], "logged_in": True})
    return {"status": "logged_in", "operator_id": user["operator_id"], "display_name": user["display_name"]}

@app.post("/auth/logout")
def auth_logout():
    save_session({"logged_in": False, "display_name": None, "operator_id": None, "email": None})
    return {"status": "logged_out"}

@app.get("/auth/me")
def auth_me():
    return get_session()

@app.get("/system/trust-summary")
def trust_summary(session=Depends(require_auth)):
    state = get_operator_state(session)
    return {"status": "ok", "operator_id": state["operator_id"], "display_name": state["display_name"], "trust_score": state["score"]["trust_score"], "audit_status": state["passport"]["audit_status"], "passport_status": state["passport"]["passport_status"], "deployment_stage": state["passport"]["deployment_stage"], "violation_count": state["violations"]["violation_count"]}

@app.get("/capital/decision")
def capital_decision(session=Depends(require_auth)):
    return get_operator_state(session)["capital_decision"]

@app.get("/broker/status")
def broker_status(session=Depends(require_auth)):
    state = get_operator_state(session)
    status = state["broker_status"]
    status["alpaca"] = alpaca_status_payload()
    return status

@app.post("/orders/place")
def place_order(payload: OrderRequest, session=Depends(require_auth)):
    decision = enforcement_check(payload.symbol, payload.side, payload.qty, session, source="strategy" if payload.strategy_id else "manual", strategy_id=payload.strategy_id)
    if not decision["allowed"]:
        raise HTTPException(status_code=403, detail={"message": "Execution blocked by enforcement", "decision": decision})
    if payload.execution_mode == "alpaca":
        return execute_real_alpaca(payload.symbol, payload.side, payload.qty, session, payload.strategy_id)
    return execute_internal_paper(payload.symbol, payload.side, payload.qty, session, payload.strategy_id)

@app.get("/orders/list")
def orders_list(session=Depends(require_auth)):
    return get_operator_state(session)["orders"]

@app.get("/positions")
def positions(session=Depends(require_auth)):
    return get_operator_state(session)["positions"]

@app.get("/portfolio")
def portfolio(session=Depends(require_auth)):
    return get_operator_state(session)["portfolio"]

@app.post("/strategies/register")
def strategies_register(payload: StrategyRegisterRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = {"strategy_id": f"strat_{uuid.uuid4().hex[:8]}", "name": payload.name, "symbol": payload.symbol.upper(), "side": payload.side.lower(), "default_qty": payload.default_qty, "enabled": payload.enabled, "created_at": now_iso(), "operator_id": session.get("operator_id")}
    state["strategies"]["strategies"].append(strategy)
    state["runtime"]["active_strategies"] = len([s for s in state["strategies"]["strategies"] if s.get("enabled")])
    save_operator_state(state)
    refresh_reports_from_state(state)
    return {"status": "registered", "strategy": strategy}

@app.get("/strategies/list")
def strategies_list(session=Depends(require_auth)):
    return get_operator_state(session)["strategies"]

@app.get("/strategies/runtime")
def strategies_runtime(session=Depends(require_auth)):
    return get_operator_state(session)["runtime"]

@app.post("/strategies/signal")
def strategies_signal(payload: SignalRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = next((s for s in state["strategies"]["strategies"] if s["strategy_id"] == payload.strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if not strategy.get("enabled"):
        raise HTTPException(status_code=400, detail="Strategy disabled")
    signal = {"signal_id": f"sig_{uuid.uuid4().hex[:8]}", "strategy_id": strategy["strategy_id"], "symbol": (payload.symbol or strategy["symbol"]).upper(), "side": (payload.side or strategy["side"]).lower(), "qty": payload.qty or strategy["default_qty"], "timestamp": now_iso(), "operator_id": session.get("operator_id"), "execution_mode": payload.execution_mode}
    state["signals"]["signals"].append(signal)
    state["runtime"]["last_signal"] = signal
    save_operator_state(state)
    return place_order(OrderRequest(symbol=signal["symbol"], side=signal["side"], qty=signal["qty"], strategy_id=signal["strategy_id"], execution_mode=payload.execution_mode), session)

@app.get("/signals")
def signals(session=Depends(require_auth)):
    return get_operator_state(session)["signals"]

@app.post("/enforcement/check")
def enforcement_endpoint(payload: OrderRequest, session=Depends(require_auth)):
    return enforcement_check(payload.symbol, payload.side, payload.qty, session, source="strategy" if payload.strategy_id else "manual", strategy_id=payload.strategy_id)

@app.get("/enforcement/status")
def enforcement_status(session=Depends(require_auth)):
    return get_operator_state(session)["enforcement"]

@app.get("/enforcement/blocked-orders")
def blocked_orders(session=Depends(require_auth)):
    return get_operator_state(session)["blocked_orders"]

@app.get("/enforcement/blocked-signals")
def blocked_signals(session=Depends(require_auth)):
    return get_operator_state(session)["blocked_signals"]

@app.get("/operator/state")
def operator_state(session=Depends(require_auth)):
    state = get_operator_state(session)
    return {"operator_id": state["operator_id"], "display_name": state["display_name"], "portfolio": state["portfolio"], "orders_count": len(state["orders"]["orders"]), "positions_count": len(state["positions"]["positions"]), "strategies_count": len(state["strategies"]["strategies"]), "signals_count": len(state["signals"]["signals"]), "blocked_orders_count": len(state["blocked_orders"]["blocked_orders"]), "blocked_signals_count": len(state["blocked_signals"]["blocked_signals"]), "allocator": state["allocator"], "broker_sync": state["broker_sync"]}

@app.get("/reports/execution-ledger")
def reports_execution_ledger(session=Depends(require_auth)):
    return get_reports(session)["execution_ledger"]

@app.get("/reports/fills")
def reports_fills(session=Depends(require_auth)):
    return get_reports(session)["fills"]

@app.get("/reports/performance")
def reports_performance(session=Depends(require_auth)):
    state = get_operator_state(session)
    return refresh_reports_from_state(state)["performance"]

@app.get("/reports/evidence-packet")
def reports_evidence_packet(session=Depends(require_auth)):
    state = get_operator_state(session)
    return refresh_reports_from_state(state)["evidence_packet"]

@app.post("/reports/generate")
def reports_generate(session=Depends(require_auth)):
    state = get_operator_state(session)
    reports = refresh_reports_from_state(state)
    return {"status": "generated", "operator_id": state["operator_id"], "generated_at": reports["evidence_packet"]["generated_at"]}

@app.get("/allocator/operators")
def allocator_operators():
    users = users_db()["users"]
    ops = []
    for u in users:
        ensure_state_for_user(u)
        state = load_json(state_filename(u["operator_id"]), {})
        ops.append({"operator_id": u["operator_id"], "display_name": u["display_name"], "trust_score": state.get("score", {}).get("trust_score", 0), "deployed_capital": state.get("allocator", {}).get("deployed_capital", 0)})
    return {"operators": ops}

@app.get("/allocator/deployments")
def allocator_deployments():
    return load_json("allocator_deployments.json", {"deployments": []})

@app.post("/allocator/request-capital")
def allocator_request(payload: AllocationRequest):
    data = load_json("allocator_deployments.json", {"deployments": []})
    item = {"allocation_id": f"alloc_{uuid.uuid4().hex[:10]}", "allocator_id": payload.allocator_id, "operator_id": payload.operator_id, "requested_capital": payload.requested_capital, "approved_capital": 0.0, "status": "REQUESTED", "mandate_name": payload.mandate_name, "created_at": now_iso()}
    data["deployments"].append(item)
    save_json("allocator_deployments.json", data)
    users = users_db()["users"]
    user = next((u for u in users if u["operator_id"] == payload.operator_id), None)
    if user:
        ensure_state_for_user(user)
        state = load_json(state_filename(payload.operator_id), {})
        state["allocator"]["requested_capital"] = payload.requested_capital
        state["allocator"]["latest_allocation_id"] = item["allocation_id"]
        state["allocator"]["status"] = "REQUESTED"
        save_json(state_filename(payload.operator_id), state)
    return {"status": "requested", "deployment": item}

@app.post("/allocator/approve-capital")
def allocator_approve(payload: ApprovalRequest):
    data = load_json("allocator_deployments.json", {"deployments": []})
    found = None
    for d in data["deployments"]:
        if d["allocation_id"] == payload.allocation_id:
            d["approved_capital"] = payload.approved_capital
            d["status"] = "APPROVED"
            d["approved_at"] = now_iso()
            found = d
            break
    save_json("allocator_deployments.json", data)
    if not found:
        raise HTTPException(status_code=404, detail="allocation not found")
    users = users_db()["users"]
    user = next((u for u in users if u["operator_id"] == found["operator_id"]), None)
    if user:
        ensure_state_for_user(user)
        state = load_json(state_filename(found["operator_id"]), {})
        state["allocator"]["deployed_capital"] = payload.approved_capital
        state["allocator"]["latest_allocation_id"] = found["allocation_id"]
        state["allocator"]["status"] = "LIVE_APPROVED"
        state["capital_decision"]["capital_allocated"] = payload.approved_capital
        state["portfolio"]["buying_power"] = max(float(state["portfolio"].get("buying_power", 0)), payload.approved_capital)
        save_json(state_filename(found["operator_id"]), state)
    packets = load_json("allocator_packets.json", {"packets": []})
    packets["packets"].append({"packet_id": f"packet_{uuid.uuid4().hex[:8]}", "allocation_id": found["allocation_id"], "operator_id": found["operator_id"], "approved_capital": payload.approved_capital, "generated_at": now_iso(), "artifacts": ["deployment_record", "capital_state"]})
    save_json("allocator_packets.json", packets)
    return {"status": "approved", "deployment": found}

@app.get("/allocator/capital-state")
def allocator_capital_state():
    users = users_db()["users"]
    rows = []
    for u in users:
        ensure_state_for_user(u)
        state = load_json(state_filename(u["operator_id"]), {})
        rows.append({"operator_id": u["operator_id"], "display_name": u["display_name"], "deployed_capital": state.get("allocator", {}).get("deployed_capital", 0), "status": state.get("allocator", {}).get("status", "NOT_DEPLOYED"), "latest_allocation_id": state.get("allocator", {}).get("latest_allocation_id")})
    return {"capital_states": rows}

@app.get("/allocator/packets")
def allocator_packets():
    return load_json("allocator_packets.json", {"packets": []})

@app.get("/broker/account-summary")
def broker_account_summary(session=Depends(require_auth)):
    state = get_operator_state(session)
    if not state["broker_sync"]["account_summary"]:
        sync_broker_state(session)
        state = get_operator_state(session)
    return state["broker_sync"]["account_summary"]

@app.get("/broker/positions")
def broker_positions(session=Depends(require_auth)):
    state = get_operator_state(session)
    if not state["broker_sync"]["synced_positions"]:
        sync_broker_state(session)
        state = get_operator_state(session)
    return {"positions": state["broker_sync"]["synced_positions"]}

@app.get("/broker/orders")
def broker_orders(session=Depends(require_auth)):
    state = get_operator_state(session)
    if not state["broker_sync"]["synced_orders"]:
        sync_broker_state(session)
        state = get_operator_state(session)
    return {"orders": state["broker_sync"]["synced_orders"]}

@app.get("/broker/pnl")
def broker_pnl(session=Depends(require_auth)):
    state = get_operator_state(session)
    if not state["broker_sync"]["pnl"].get("equity"):
        sync_broker_state(session)
        state = get_operator_state(session)
    return state["broker_sync"]["pnl"]

@app.post("/broker/sync")
def broker_sync(session=Depends(require_auth)):
    return sync_broker_state(session)

@app.get("/broker/reconciliation")
def broker_reconciliation(session=Depends(require_auth)):
    state = get_operator_state(session)
    if not state["broker_sync"]["last_synced_at"]:
        sync_broker_state(session)
        state = get_operator_state(session)
    return state["broker_sync"]["reconciliation"]

@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"status": "ok", "message": "Quantora QNT30311 live"}

@app.get("/{page_name}")
def static_pages(page_name: str):
    page = FRONTEND_DIR / page_name
    if page.suffix == "" and not page_name.endswith(".html"):
        page = FRONTEND_DIR / f"{page_name}.html"
    if page.exists() and page.is_file():
        return FileResponse(page)
    return JSONResponse({"error": "not found", "page": page_name}, status_code=404)
