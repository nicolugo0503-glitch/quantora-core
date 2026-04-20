import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)
assert client.get('/').status_code == 200
assert client.get('/adaptive-execution/status').status_code == 200
assert client.get('/allocation/status').status_code == 200
assert client.get('/autonomous-execution/status').status_code == 200
assert client.get('/broker-integration/status').status_code == 200
assert client.get('/performance/status').status_code == 200
assert client.get('/portfolio-manager/status').status_code == 200
assert client.get('/product/status').status_code == 200
assert client.get('/monetization/status').status_code == 200
assert client.get('/control-plane/health').status_code == 200
assert client.get('/identity/status').status_code == 200
assert client.get('/data-layer/status').status_code == 200
assert client.get('/payments/status').status_code == 200
assert client.get('/launch/status').status_code == 200
print('full audit fix smoke test passed')
