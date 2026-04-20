import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "capital_committee_engine.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "committee_engine": {
            "enabled": True,
            "last_updated_at": None,
            "last_vote_at": None,
            "last_compile_at": None,
            "committee_count": 0,
            "proposal_count": 0,
            "vote_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "telemetry": [],
        },
        "committees": [],
        "proposals": [],
        "routing": {
            "default_quorum": 2,
            "approval_threshold": 0.6,
            "auto_compile_on_quorum": True,
            "allow_tie_reject": True,
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
    for k, v in default_state()["committee_engine"].items():
        merged["committee_engine"].setdefault(k, v)
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


def _committee_summary(state):
    proposals = state.get("proposals", [])
    approved = len([p for p in proposals if p.get("status") == "approved"])
    rejected = len([p for p in proposals if p.get("status") == "rejected"])
    pending = len([p for p in proposals if p.get("status") in ("draft", "voting")])
    return approved, rejected, pending


def upsert_committees(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    committees = state.get("committees", [])
    for item in payload.get("committees", []):
        committee_id = item.get("committee_id") or f"committee_{len(committees)+1:03d}"
        item["committee_id"] = committee_id
        item["name"] = item.get("name") or committee_id
        item["members"] = item.get("members") or []
        item["quorum"] = max(int(item.get("quorum") or state["routing"]["default_quorum"]), 1)
        item["approval_threshold"] = _safe_float(item.get("approval_threshold"), state["routing"]["approval_threshold"])
        existing = next((x for x in committees if x.get("committee_id") == committee_id), None)
        if existing:
            existing.update(item)
        else:
            committees.append(item)
    state["committees"] = committees
    state["committee_engine"]["committee_count"] = len(committees)
    state["committee_engine"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "committees.upserted", "count": len(payload.get("committees", []))})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "committees_upserted", "committee_count": len(committees)}


def create_proposal(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    proposal = deepcopy(payload)
    proposal["proposal_id"] = proposal.get("proposal_id") or f"proposal_{len(state.get('proposals', []))+1:04d}"
    proposal["committee_id"] = proposal.get("committee_id") or "capital_committee_primary"
    proposal["title"] = proposal.get("title") or proposal["proposal_id"]
    proposal["requested_capital"] = _safe_float(proposal.get("requested_capital"), 0.0)
    proposal["status"] = proposal.get("status") or "draft"
    proposal["votes"] = proposal.get("votes") or []
    proposal["created_at"] = proposal.get("created_at") or now_iso()
    proposal["compiled_allocation"] = proposal.get("compiled_allocation") or {}
    state.setdefault("proposals", []).append(proposal)
    state["committee_engine"]["proposal_count"] = len(state["proposals"])
    state["committee_engine"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "proposal.created", "proposal_id": proposal["proposal_id"]})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "proposal_created", "proposal": proposal}


def cast_vote(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    proposal = next((p for p in state.get("proposals", []) if p.get("proposal_id") == payload.get("proposal_id")), None)
    if not proposal:
        return {"status": "error", "message": "proposal_not_found"}
    committee = next((c for c in state.get("committees", []) if c.get("committee_id") == proposal.get("committee_id")), None)
    if not committee:
        return {"status": "error", "message": "committee_not_found"}

    vote = {
        "member_id": payload.get("member_id") or "member_unknown",
        "decision": (payload.get("decision") or "hold").lower(),
        "weight": _safe_float(payload.get("weight"), 1.0),
        "comment": payload.get("comment"),
        "timestamp": now_iso(),
    }
    proposal.setdefault("votes", [])
    existing = next((v for v in proposal["votes"] if v.get("member_id") == vote["member_id"]), None)
    if existing:
        existing.update(vote)
    else:
        proposal["votes"].append(vote)
    proposal["status"] = "voting"

    yes_weight = sum(v.get("weight", 0.0) for v in proposal["votes"] if v.get("decision") == "approve")
    no_weight = sum(v.get("weight", 0.0) for v in proposal["votes"] if v.get("decision") == "reject")
    total_weight = yes_weight + no_weight
    quorum_met = len(proposal["votes"]) >= max(int(committee.get("quorum", 1)), 1)
    approve_ratio = (yes_weight / total_weight) if total_weight > 0 else 0.0

    state["committee_engine"]["vote_count"] = sum(len(p.get("votes", [])) for p in state.get("proposals", []))
    state["committee_engine"]["last_vote_at"] = now_iso()
    state["committee_engine"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "vote.cast", "proposal_id": proposal["proposal_id"], "member_id": vote["member_id"]})
    state["history"] = state["history"][-100:]

    if quorum_met and state["routing"].get("auto_compile_on_quorum"):
        proposal["status"] = "approved" if approve_ratio >= _safe_float(committee.get("approval_threshold"), 0.6) else "rejected"
        proposal["compiled_allocation"] = {
            "recommended_capital": round(proposal["requested_capital"] * (approve_ratio if proposal["status"] == "approved" else 0.0), 2),
            "approve_ratio": round(approve_ratio, 4),
            "yes_weight": round(yes_weight, 2),
            "no_weight": round(no_weight, 2),
            "compiled_at": now_iso(),
        }
        state["committee_engine"]["last_compile_at"] = now_iso()

    approved, rejected, _ = _committee_summary(state)
    state["committee_engine"]["approved_count"] = approved
    state["committee_engine"]["rejected_count"] = rejected
    save_state(artifacts_dir, state)
    return {
        "status": "vote_cast",
        "proposal_id": proposal["proposal_id"],
        "proposal_status": proposal["status"],
        "quorum_met": quorum_met,
        "approve_ratio": round(approve_ratio, 4),
        "compiled_allocation": proposal.get("compiled_allocation", {}),
        "votes": proposal.get("votes", []),
    }


def compile_allocation(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    proposal = next((p for p in state.get("proposals", []) if p.get("proposal_id") == payload.get("proposal_id")), None)
    if not proposal:
        return {"status": "error", "message": "proposal_not_found"}
    committee = next((c for c in state.get("committees", []) if c.get("committee_id") == proposal.get("committee_id")), None)
    if not committee:
        return {"status": "error", "message": "committee_not_found"}

    yes_weight = sum(v.get("weight", 0.0) for v in proposal.get("votes", []) if v.get("decision") == "approve")
    no_weight = sum(v.get("weight", 0.0) for v in proposal.get("votes", []) if v.get("decision") == "reject")
    total_weight = yes_weight + no_weight
    approve_ratio = (yes_weight / total_weight) if total_weight > 0 else 0.0
    threshold = _safe_float(committee.get("approval_threshold"), state["routing"]["approval_threshold"])
    approved = approve_ratio >= threshold and len(proposal.get("votes", [])) >= max(int(committee.get("quorum", 1)), 1)

    proposal["status"] = "approved" if approved else "rejected"
    proposal["compiled_allocation"] = {
        "recommended_capital": round(proposal.get("requested_capital", 0.0) * (approve_ratio if approved else 0.0), 2),
        "requested_capital": proposal.get("requested_capital", 0.0),
        "approve_ratio": round(approve_ratio, 4),
        "yes_weight": round(yes_weight, 2),
        "no_weight": round(no_weight, 2),
        "compiled_at": now_iso(),
        "allocation_action": "increase" if approved else "hold",
    }

    state["committee_engine"]["last_compile_at"] = now_iso()
    state["committee_engine"]["last_updated_at"] = now_iso()
    approved_count, rejected_count, _ = _committee_summary(state)
    state["committee_engine"]["approved_count"] = approved_count
    state["committee_engine"]["rejected_count"] = rejected_count
    state["history"].append({"timestamp": now_iso(), "event": "allocation.compiled", "proposal_id": proposal["proposal_id"], "status": proposal["status"]})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "allocation_compiled", "proposal": proposal}


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    approved, rejected, pending = _committee_summary(state)
    return {
        "committee_engine": state["committee_engine"],
        "routing": state["routing"],
        "committee_count": len(state.get("committees", [])),
        "proposal_count": len(state.get("proposals", [])),
        "approved_count": approved,
        "rejected_count": rejected,
        "pending_count": pending,
        "recent_proposals": state.get("proposals", [])[-10:][::-1],
    }
