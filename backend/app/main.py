import datetime
import json
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

app = FastAPI(title="Quantora QNT30322 Unified Command Center", version="30322")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_EMAILS = {"admin@quantora.local", "nicolugo0503@gmail.com"}
PRICE_BOOK = {"AAPL": 180.0, "TSLA": 175.0, "SPY": 510.0, "NVDA": 910.0, "MSFT": 420.0, "AMZN": 185.0, "META": 505.0}


def now_dt():
    return datetime.datetime.utcnow().replace(microsecond=0)


def now_iso():
    return now_dt().isoformat() + "Z"


def load_json(filename, fallback):
    path = ARTIFACTS_DIR / filename
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def save_json(filename, data):
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


def default_operator_state(operator_id, display_name):
    return {
        "operator_id": operator_id,
        "display_name": display_name,
        "capital_decision": {"approved": True, "capital_allocated": 16195},
        "strategies": {"strategies": []},
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


def ensure_state_for_user(user):
    operator_id = user["operator_id"]
    if load_json(state_filename(operator_id), None) is None:
        save_json(state_filename(operator_id), default_operator_state(operator_id, user["display_name"]))


def get_operator_by_id(operator_id):
    users = users_db()
    user = next((u for u in users["users"] if u["operator_id"] == operator_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found")
    ensure_state_for_user(user)
    return user


def get_operator_state_by_id(operator_id):
    get_operator_by_id(operator_id)
    return load_json(state_filename(operator_id), {})


def get_operator_state(session):
    return get_operator_state_by_id(session.get("operator_id"))


def save_operator_state(state):
    save_json(state_filename(state["operator_id"]), state)


def policy_for(policy_type):
    for policy in get_policies()["policies"]:
        if policy["policy_type"] == policy_type and policy.get("enabled"):
            return policy
    return None


def get_price(symbol):
    return PRICE_BOOK.get(symbol.upper(), 100.0)


def operator_exposure(state):
    total = 0.0
    count = 0
    for order in state["orders"]["orders"]:
        if order.get("status") in ["filled", "accepted", "submitted"]:
            total += float(order.get("notional", 0))
            count += 1
    return {"notional": round(total, 2), "orders": count}


def evaluate_monitoring(state):
    exposure = operator_exposure(state)
    allocated = float(state["allocator_caps"]["operator"].get("allocated_capital", 0) or 0)
    utilization = round((exposure["notional"] / allocated) * 100, 2) if allocated > 0 else 0.0
    alerts = []
    if utilization >= 80 and allocated > 0:
        alerts.append({"level": "warn", "type": "operator-utilization", "message": f"Operator utilization at {utilization}%"})
    if state["strategy_loop"].get("running") and not state["strategy_loop"].get("heartbeat_at"):
        alerts.append({"level": "warn", "type": "loop-heartbeat", "message": "Loop is marked running without heartbeat"})
    state["monitoring"]["latest_snapshot"] = {
        "timestamp": now_iso(),
        "order_count": exposure["orders"],
        "used_capital": exposure["notional"],
        "allocated_capital": allocated,
        "remaining_capital": round(allocated - exposure["notional"], 2),
        "utilization_pct": utilization,
        "alerts_count": len(alerts),
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


def control_tower_view():
    users = users_db()["users"]
    operators = []
    totals = {"operators": 0, "orders": 0, "allocated_capital": 0.0, "used_capital": 0.0, "alerts": 0, "running_loops": 0}
    for user in users:
        ensure_state_for_user(user)
        state = load_json(state_filename(user["operator_id"]), {})
        monitoring = evaluate_monitoring(state)
        save_operator_state(state)
        exposure = operator_exposure(state)
        allocated = float(state["allocator_caps"]["operator"].get("allocated_capital", 0) or 0)
        row = {
            "operator_id": user["operator_id"],
            "display_name": user["display_name"],
            "email": user["email"],
            "orders": len(state["orders"]["orders"]),
            "strategies": len(state["strategies"]["strategies"]),
            "allocated_capital": allocated,
            "used_capital": exposure["notional"],
            "remaining_capital": round(allocated - exposure["notional"], 2),
            "loop_running": state["strategy_loop"]["running"],
            "alerts": len(monitoring["alerts"]),
            "execution_mode": state["strategy_loop"].get("execution_mode"),
            "last_run_at": state["strategy_loop"].get("last_run_at"),
        }
        operators.append(row)
        totals["operators"] += 1
        totals["orders"] += row["orders"]
        totals["allocated_capital"] += allocated
        totals["used_capital"] += exposure["notional"]
        totals["alerts"] += row["alerts"]
        if row["loop_running"]:
            totals["running_loops"] += 1
    totals["remaining_capital"] = round(totals["allocated_capital"] - totals["used_capital"], 2)
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


def run_strategies_for_state(state, execution_mode, actor_email, actor_operator_id, source_action):
    strategies = [s for s in state["strategies"]["strategies"] if s.get("enabled")]
    executed_orders = []
    state["strategy_loop"]["last_run_at"] = now_iso()
    state["strategy_loop"]["heartbeat_at"] = now_iso()
    state["strategy_loop"]["total_runs"] += 1
    state["strategy_loop"]["total_signals"] += len(strategies)
    for strategy in strategies:
        notional = round(get_price(strategy["symbol"]) * int(strategy["default_qty"]), 2)
        order = {
            "order_id": f"ord_{uuid.uuid4().hex[:10]}",
            "strategy_id": strategy["strategy_id"],
            "symbol": strategy["symbol"],
            "side": strategy["side"],
            "qty": strategy["default_qty"],
            "notional": notional,
            "status": "filled",
            "mode": execution_mode,
            "timestamp": now_iso(),
        }
        state["orders"]["orders"].insert(0, order)
        executed_orders.append(order)
        state["strategy_loop"]["total_orders"] += 1
        append_governance_event(actor_email, actor_operator_id, source_action, state["operator_id"], order, "execution")
    evaluate_monitoring(state)
    save_operator_state(state)
    return executed_orders


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


def build_operator_workspace(state):
    monitoring = evaluate_monitoring(state)
    save_operator_state(state)
    strategies = state["strategies"]["strategies"]
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
        "strategies": strategies,
        "strategy_loop": state["strategy_loop"],
        "orders": orders,
        "monitoring": monitoring,
        "execution_summary": {
            "recent_orders": len(orders),
            "enabled_strategies": len([s for s in strategies if s.get("enabled")]),
            "total_orders": state["strategy_loop"].get("total_orders", 0),
        },
    }


def build_command_center_snapshot(session):
    users = users_db()["users"]
    state = get_operator_state(session)
    workspace = build_operator_workspace(state)
    approvals = get_approvals()["requests"]
    ledger = load_json("governance_ledger.json", {"events": []})["events"]
    pending = [r for r in approvals if r.get("status") == "PENDING"]
    snapshot = {
        "session": {**session, "is_admin": session.get("email") in ADMIN_EMAILS},
        "north_star": {
            "mission": "QNT30322 Unified Command Center",
            "system": "Quantora multi-layer institutional trading operating system",
            "timestamp": now_iso(),
        },
        "personal_workspace": workspace,
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
            "layer": "qnt30322-unified-command-center",
        },
    }
    if session.get("email") in ADMIN_EMAILS:
        snapshot["control_tower"] = control_tower_view()
    return snapshot


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


class StrategyToggleRequest(BaseModel):
    strategy_id: str
    enabled: bool


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


@app.get("/health")
def health():
    return {"status": "ok", "layer": "qnt30322-unified-command-center"}


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
        "created_at": now_iso(),
        "operator_id": session.get("operator_id"),
    }
    state["strategies"]["strategies"].append(strategy)
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "strategy.register", strategy["strategy_id"], strategy, "strategy")
    return {"status": "registered", "strategy": strategy}


@app.get("/strategies/list")
def strategies_list(session=Depends(require_auth)):
    return get_operator_state(session)["strategies"]


@app.post("/strategies/toggle")
def strategies_toggle(payload: StrategyToggleRequest, session=Depends(require_auth)):
    state = get_operator_state(session)
    strategy = next((s for s in state["strategies"]["strategies"] if s["strategy_id"] == payload.strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy["enabled"] = payload.enabled
    save_operator_state(state)
    append_governance_event(session.get("email"), session.get("operator_id"), "strategy.toggle", strategy["strategy_id"], strategy, "strategy")
    return {"status": "updated", "strategy": strategy}


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


@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"status": "ok", "message": "Quantora QNT30322 live"}


@app.get("/{page_name}")
def static_pages(page_name: str):
    page = FRONTEND_DIR / page_name
    if page.suffix == "" and not page_name.endswith(".html"):
        page = FRONTEND_DIR / f"{page_name}.html"
    if page.exists() and page.is_file():
        return FileResponse(page)
    return JSONResponse({"error": "not found", "page": page_name}, status_code=404)
