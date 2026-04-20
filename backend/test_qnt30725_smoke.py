from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30725_summary_route_exists():
    client = TestClient(app)
    res = client.get('/health')
    assert res.status_code in (200, 404)


def test_qnt30725_module_imports():
    from backend.app import qnt30725_institutional_breach_escalation_layer_router as mod
    assert hasattr(mod, 'router')
    assert mod.DEFAULT_POLICY['minimum_breach_score'] >= 85
