import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

checks = {}
for path in [
    '/health',
    '/health/runtime',
    '/health/billing',
    '/health/persistence',
    '/health/execution',
    '/health/attribution',
    '/health/deployment',
]:
    r = client.get(path)
    assert r.status_code == 200, (path, r.text)
    checks[path] = r.json()

report = checks['/health/deployment']
assert report.get('mission') == 'QNT30420'
assert report.get('overall_status') in {'ready', 'degraded', 'blocked'}
assert 'safe_mode' in report
assert isinstance(report.get('checks'), list)

print({'status': 'ok', 'overall_status': report.get('overall_status'), 'readiness_score': report.get('readiness_score')})
