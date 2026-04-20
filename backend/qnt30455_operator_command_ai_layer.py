from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _round(value: float) -> float:
    return round(float(value), 2)


def build_operator_ai_package(
    commands: Iterable[Dict],
    copilots: Iterable[Dict],
    recommendations: Iterable[Dict],
    decision_logs: Iterable[Dict],
) -> Dict:
    commands = list(commands or [])
    copilots = list(copilots or [])
    recommendations = list(recommendations or [])
    decision_logs = list(decision_logs or [])

    successful_commands = [c for c in commands if (c.get("status") or "").lower() in {"completed", "executed", "applied"}]
    pending_commands = [c for c in commands if (c.get("status") or "").lower() in {"queued", "pending", "draft"}]
    active_copilots = [c for c in copilots if (c.get("status") or "").lower() in {"active", "ready", "online"}]
    accepted_recommendations = [r for r in recommendations if (r.get("status") or "").lower() in {"accepted", "approved", "applied"}]

    command_rows: List[Dict] = []
    for row in commands:
        command_rows.append({
            "command_id": row.get("id"),
            "command_name": row.get("command_name") or "operator_command",
            "command_type": row.get("command_type") or "analysis",
            "target_system": row.get("target_system") or "global",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    copilot_rows: List[Dict] = []
    for row in copilots:
        copilot_rows.append({
            "copilot_id": row.get("id"),
            "copilot_name": row.get("copilot_name") or "quantora_copilot",
            "specialty": row.get("specialty") or "operations",
            "status": row.get("status") or "draft",
            "confidence_score": round(_as_float(row.get("confidence_score")), 2),
            "created_at": row.get("created_at"),
        })

    recommendation_rows: List[Dict] = []
    for row in recommendations:
        recommendation_rows.append({
            "recommendation_id": row.get("id"),
            "recommendation_name": row.get("recommendation_name") or "recommendation",
            "priority": row.get("priority") or "medium",
            "status": row.get("status") or "proposed",
            "target_ref": row.get("target_ref") or "-",
            "created_at": row.get("created_at"),
        })

    decision_rows: List[Dict] = []
    for row in decision_logs:
        decision_rows.append({
            "decision_id": row.get("id"),
            "decision_name": row.get("decision_name") or "decision",
            "operator_action": row.get("operator_action") or "reviewed",
            "outcome": row.get("outcome") or "logged",
            "created_at": row.get("created_at"),
        })

    ai_score = max(
        45,
        min(
            100,
            int(
                55
                + len(active_copilots) * 5
                + len(successful_commands) * 3
                + len(accepted_recommendations) * 2
                + len(decision_logs)
                - len(pending_commands)
            )
        ),
    )

    return {
        "summary": {
            "commands_total": len(commands),
            "commands_successful": len(successful_commands),
            "commands_pending": len(pending_commands),
            "copilots_active": len(active_copilots),
            "recommendations_total": len(recommendations),
            "accepted_recommendations": len(accepted_recommendations),
            "decision_logs": len(decision_logs),
            "ai_score": ai_score,
        },
        "commands": command_rows,
        "copilots": copilot_rows,
        "recommendations": recommendation_rows,
        "decision_logs": decision_rows,
        "ai_health": {
            "command_registry_ready": bool(commands),
            "copilot_registry_ready": bool(copilots),
            "recommendation_engine_ready": bool(recommendations),
            "decision_memory_ready": bool(decision_logs),
            "ai_score": ai_score,
        },
    }
