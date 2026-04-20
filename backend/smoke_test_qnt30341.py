
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app


def main():
    with TestClient(app) as client:
        # create user session
        client.post('/auth/register', json={'display_name': 'stability', 'email': 'stability@quantora.local', 'password': 'test1234'})
        client.post('/auth/login', json={'email': 'stability@quantora.local', 'password': 'test1234'})
        client.post('/capital-source/update', json={'mode': 'broker'})
        status = client.get('/stability/status').json()
        sync = client.post('/stability/sync-now').json()
        assert 'truth' in status
        assert 'guard' in sync
        print({'status': status.get('status'), 'guard': sync.get('guard', {}).get('status'), 'mismatches': sync.get('truth', {}).get('counts', {}).get('mismatches')})


if __name__ == '__main__':
    main()
