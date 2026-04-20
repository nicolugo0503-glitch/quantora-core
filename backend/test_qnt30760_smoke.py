from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30760_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/regulatory-liquidity-stress-command-recovery-layer/summary" in routes
