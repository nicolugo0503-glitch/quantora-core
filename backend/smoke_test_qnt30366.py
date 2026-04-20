from pathlib import Path
try:
    from release_audit import build_release_audit
except Exception:
    from backend.release_audit import build_release_audit

PROJECT_DIR = Path(__file__).resolve().parent.parent

def run():
    audit = build_release_audit(PROJECT_DIR)
    assert audit["release"]["release_id"] == "QNT30366"
    assert audit["backend"]["expected_endpoints_present"]["/strategy-factory/status"] is True
    assert audit["backend"]["expected_endpoints_present"]["/capital-committee/status"] is True
    assert audit["backend"]["expected_endpoints_present"]["/command-mesh/status"] is True
    assert audit["summary"]["panel_coverage_pct"] >= 100.0
    assert audit["summary"]["stale_marker_count"] == 0, audit
    print("QNT30366 smoke test passed")

if __name__ == "__main__":
    run()
