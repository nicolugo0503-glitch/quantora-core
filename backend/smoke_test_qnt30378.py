from pathlib import Path
try:
    from execution_drift_monitor import build_status, capture_snapshot, evaluate_drift
except Exception:
    from backend.execution_drift_monitor import build_status, capture_snapshot, evaluate_drift

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    snap = capture_snapshot(ARTIFACTS, {
        "symbol":"AAPL",
        "baseline_slippage_bps":12.0,
        "current_slippage_bps":24.5,
        "baseline_latency_ms":420,
        "current_latency_ms":690,
        "baseline_fill_rate":0.96,
        "current_fill_rate":0.87,
        "baseline_regime_vol":0.22,
        "current_regime_vol":0.46,
    })
    assert snap["status"] == "snapshot_captured"
    alert = evaluate_drift(ARTIFACTS, {})
    assert alert["status"] == "drift_evaluated"
    assert alert["alert"]["triggered"] is True
    status = build_status(ARTIFACTS)
    assert status["snapshot_count"] >= 1
    assert status["alert_count"] >= 1
    print("QNT30378 smoke test passed")

if __name__ == "__main__":
    run()
