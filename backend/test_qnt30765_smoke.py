from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30765_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/regulatory-data-lineage-evidence-provenance-attestation-fabric/summary" in routes
