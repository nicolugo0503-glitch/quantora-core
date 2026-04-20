from pathlib import Path
try:
    from operator_command_mesh import upsert_mandates, route_command, execute_pending, build_status
except Exception:
    from backend.operator_command_mesh import upsert_mandates, route_command, execute_pending, build_status

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    res = upsert_mandates(ARTIFACTS, {
        "operators": [{"operator_id":"operator_alpha","display_name":"Operator Alpha","tier":"delegate"}],
        "mandates": [{"operator_id":"operator_alpha","scope":"equities","allowed_modes":["paper","live"],"max_notional":15000,"active":True}]
    })
    assert res["active_mandates"] >= 1
    routed_live = route_command(ARTIFACTS, {
        "command": {"operator_id":"operator_alpha","action":"buy","symbol":"AAPL","execution_mode":"live","priority":"high","notional":12000}
    })
    assert routed_live["command"]["status"] == "pending"
    routed_block = route_command(ARTIFACTS, {
        "command": {"operator_id":"operator_alpha","action":"buy","symbol":"NVDA","execution_mode":"live","priority":"high","notional":30000}
    })
    assert routed_block["command"]["status"] == "blocked"
    routed_paper = route_command(ARTIFACTS, {
        "command": {"operator_id":"operator_alpha","action":"sell","symbol":"TSLA","execution_mode":"paper","priority":"normal","notional":5000}
    })
    assert routed_paper["command"]["status"] == "executed"
    execd = execute_pending(ARTIFACTS, {"approve_live": True})
    assert execd["count"] >= 1
    status = build_status(ARTIFACTS)
    assert status["operator_count"] >= 1
    print("QNT30362 smoke test passed")

if __name__ == "__main__":
    run()
