from fastapi.testclient import TestClient
from backend.app.main import app


def run():
    client = TestClient(app)
    # public unauthenticated route should exist but require auth or return structured response
    spec = client.get('/openapi.json')
    assert spec.status_code == 200
    paths = spec.json().get('paths', {})
    assert '/performance/live-status' in paths
    assert '/performance/metrics' in paths
    print('qnt30345 smoke test passed')


if __name__ == '__main__':
    run()
