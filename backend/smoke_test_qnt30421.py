import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

status = client.get('/live-execution/status')
assert status.status_code == 200, status.text
payload = status.json()
assert payload.get('mission') == 'QNT30421'
assert 'readiness' in payload
assert 'execution' in payload

ready = client.get('/live-execution/readiness')
assert ready.status_code == 200, ready.text

orders = client.get('/live-execution/orders')
assert orders.status_code == 200, orders.text
assert orders.json().get('mission') == 'QNT30421'

print('QNT30421 smoke test passed')
