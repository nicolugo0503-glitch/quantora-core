from backend.app.main import app

def test_qnt30427_routes_present():
    paths = {route.path for route in app.routes}
    assert '/workspace/portfolio/exposure' in paths
    assert '/workspace/portfolio/risk' in paths
