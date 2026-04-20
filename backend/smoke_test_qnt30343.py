from pathlib import Path
from backend.automation_engine import QuantoraAutomationEngine


def now_iso():
    return "2026-03-27T00:00:00Z"


def run_cycle(operator_id, cfg):
    return {
        "operator_id": operator_id,
        "execution_mode": cfg.get("execution_mode"),
        "broker_reconcile_enabled": cfg.get("broker_reconcile_enabled"),
        "pnl_sync_enabled": cfg.get("pnl_sync_enabled"),
        "status": "ok",
    }


if __name__ == "__main__":
    state_file = Path("/tmp/qnt30343_automation_state.json")
    if state_file.exists():
        state_file.unlink()
    engine = QuantoraAutomationEngine(state_file, run_cycle, now_iso)
    engine.ensure_operator("operator_test")
    engine.configure_operator("operator_test", {
        "execution_mode": "alpaca",
        "interval_seconds": 15,
        "broker_reconcile_enabled": True,
        "pnl_sync_enabled": True,
    })
    started = engine.start_operator("operator_test")
    assert started["enabled"] is True
    result = engine.tick("operator_test", force=True)
    assert result["count"] == 1
    assert result["results"][0]["status"] == "completed"
    stopped = engine.stop_operator("operator_test")
    assert stopped["enabled"] is False
    print("QNT30343 smoke test passed")
