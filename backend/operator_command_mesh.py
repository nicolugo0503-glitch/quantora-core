import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "operator_command_mesh.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "command_mesh": {
            "enabled": True,
            "last_updated_at": None,
            "last_dispatch_at": None,
            "last_mandate_sync_at": None,
            "command_count": 0,
            "delegation_count": 0,
            "blocked_commands": 0,
            "executed_commands": 0,
            "telemetry": [],
        },
        "operators": [],
        "mandates": [],
        "commands": [],
        "routing": {
            "default_priority": "normal",
            "require_mandate_for_live": True,
            "risk_gate_required": True,
            "approval_gate_required": True,
            "max_live_notional_per_command": 25000.0,
        },
        "history": [],
    }


def _ensure_state_file(artifacts_dir: Path):
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / STATE_FILE_NAME
    if not path.exists():
        path.write_text(json.dumps(default_state(), indent=2), encoding="utf-8")
    return path


def load_state(artifacts_dir: Path):
    path = _ensure_state_file(artifacts_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = default_state()
    merged = default_state()
    merged.update({k: v for k, v in data.items() if k in merged})
    for k, v in default_state()["command_mesh"].items():
        merged["command_mesh"].setdefault(k, v)
    for k, v in default_state()["routing"].items():
        merged["routing"].setdefault(k, v)
    return merged


def save_state(artifacts_dir: Path, state):
    path = _ensure_state_file(artifacts_dir)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _safe_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def upsert_mandates(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    mandates = state.get("mandates", [])
    operators = state.get("operators", [])
    seen_operator_ids = {o.get("operator_id") for o in operators}

    for op in payload.get("operators", []):
        operator_id = op.get("operator_id")
        if not operator_id:
            continue
        existing = next((x for x in operators if x.get("operator_id") == operator_id), None)
        if existing:
            existing.update(op)
        else:
            operators.append(op)
        seen_operator_ids.add(operator_id)

    for item in payload.get("mandates", []):
        mandate_id = item.get("mandate_id") or f"mandate_{len(mandates)+1:03d}"
        item["mandate_id"] = mandate_id
        item["operator_id"] = item.get("operator_id") or "operator_primary"
        item["scope"] = item.get("scope") or "portfolio"
        item["allowed_modes"] = item.get("allowed_modes") or ["paper"]
        item["max_notional"] = _safe_float(item.get("max_notional"), 10000.0)
        item["active"] = bool(item.get("active", True))
        existing = next((x for x in mandates if x.get("mandate_id") == mandate_id), None)
        if existing:
            existing.update(item)
        else:
            mandates.append(item)
        if item["operator_id"] not in seen_operator_ids:
            operators.append({"operator_id": item["operator_id"], "display_name": item["operator_id"], "tier": "delegate"})
            seen_operator_ids.add(item["operator_id"])

    state["operators"] = operators
    state["mandates"] = mandates
    state["command_mesh"]["delegation_count"] = len([m for m in mandates if m.get("active")])
    state["command_mesh"]["last_mandate_sync_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "mandates.upserted", "count": len(payload.get("mandates", []))})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {
        "status": "mandates_upserted",
        "operator_count": len(operators),
        "mandate_count": len(mandates),
        "active_mandates": len([m for m in mandates if m.get("active")]),
    }


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    commands = state.get("commands", [])
    pending = [c for c in commands if c.get("status") == "pending"]
    blocked = [c for c in commands if c.get("status") == "blocked"]
    executed = [c for c in commands if c.get("status") == "executed"]
    return {
        "command_mesh": state["command_mesh"],
        "routing": state["routing"],
        "operator_count": len(state.get("operators", [])),
        "mandate_count": len(state.get("mandates", [])),
        "pending_commands": len(pending),
        "blocked_commands": len(blocked),
        "executed_commands": len(executed),
        "recent_commands": commands[-10:][::-1],
    }


def route_command(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    routing = state["routing"]
    for key in ["default_priority", "require_mandate_for_live", "risk_gate_required", "approval_gate_required", "max_live_notional_per_command"]:
        if key in payload and payload[key] is not None:
            routing[key] = payload[key]

    command = deepcopy(payload.get("command") or {})
    operator_id = command.get("operator_id") or "operator_primary"
    execution_mode = (command.get("execution_mode") or "paper").lower()
    action = command.get("action") or "hold"
    symbol = (command.get("symbol") or "AAPL").upper()
    notional = _safe_float(command.get("notional"), 0.0)
    priority = command.get("priority") or routing["default_priority"]

    matching = [m for m in state.get("mandates", []) if m.get("operator_id") == operator_id and m.get("active")]
    mandate_ok = True
    mandate_reason = "ok"
    if execution_mode == "live" and routing.get("require_mandate_for_live"):
        if not matching:
            mandate_ok = False
            mandate_reason = "missing_live_mandate"
        else:
            live_allowed = any("live" in [x.lower() for x in m.get("allowed_modes", [])] and notional <= _safe_float(m.get("max_notional"), 0.0) for m in matching)
            if not live_allowed:
                mandate_ok = False
                mandate_reason = "live_mandate_limit_exceeded"

    risk_ok = notional <= _safe_float(routing.get("max_live_notional_per_command"), 25000.0)
    approval_required = execution_mode == "live" and routing.get("approval_gate_required")
    status = "pending"
    reasons = []

    if not mandate_ok:
        status = "blocked"
        reasons.append(mandate_reason)
    if execution_mode == "live" and not risk_ok:
        status = "blocked"
        reasons.append("risk_notional_limit_exceeded")
    if approval_required and status != "blocked":
        reasons.append("approval_required")
    if execution_mode == "paper" and status != "blocked":
        status = "executed"
    elif execution_mode == "live" and status != "blocked":
        status = "pending"

    cmd = {
        "command_id": command.get("command_id") or f"cmd_{len(state.get('commands', []))+1:04d}",
        "timestamp": now_iso(),
        "operator_id": operator_id,
        "action": action,
        "symbol": symbol,
        "execution_mode": execution_mode,
        "priority": priority,
        "notional": notional,
        "status": status,
        "reasons": reasons,
    }
    state.setdefault("commands", []).append(cmd)
    mesh = state["command_mesh"]
    mesh["last_updated_at"] = now_iso()
    mesh["last_dispatch_at"] = now_iso()
    mesh["command_count"] = len(state["commands"])
    mesh["blocked_commands"] = len([c for c in state["commands"] if c.get("status") == "blocked"])
    mesh["executed_commands"] = len([c for c in state["commands"] if c.get("status") == "executed"])
    mesh["telemetry"].append({
        "timestamp": now_iso(),
        "event": "command.routed",
        "status": status,
        "execution_mode": execution_mode,
        "operator_id": operator_id,
    })
    mesh["telemetry"] = mesh["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "command.routed", "command_id": cmd["command_id"], "status": status})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {
        "status": "routed",
        "command": cmd,
        "routing": routing,
        "mandate_ok": mandate_ok,
        "risk_ok": risk_ok,
        "approval_required": approval_required,
    }


def execute_pending(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    approve_live = bool(payload.get("approve_live", False))
    executed = []
    for cmd in state.get("commands", []):
        if cmd.get("status") == "pending":
            if cmd.get("execution_mode") == "live" and not approve_live:
                continue
            cmd["status"] = "executed"
            cmd["executed_at"] = now_iso()
            cmd["execution_note"] = "delegated_command_mesh_execution"
            executed.append(cmd["command_id"])
    mesh = state["command_mesh"]
    mesh["executed_commands"] = len([c for c in state["commands"] if c.get("status") == "executed"])
    mesh["last_updated_at"] = now_iso()
    mesh["telemetry"].append({"timestamp": now_iso(), "event": "commands.executed", "count": len(executed)})
    mesh["telemetry"] = mesh["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "commands.executed", "count": len(executed)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "executed", "executed_command_ids": executed, "count": len(executed)}
