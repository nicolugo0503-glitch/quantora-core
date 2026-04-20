import uuid
from fastapi.testclient import TestClient
from backend.app.main import app


def run():
    with TestClient(app) as client:
        spec = client.get('/openapi.json')
        assert spec.status_code == 200
        paths = spec.json().get('paths', {})
        assert '/automation/health' in paths
        assert '/automation/cycle-metrics' in paths
        assert '/automation/recover' in paths

        email = f"stability-{uuid.uuid4().hex[:8]}@quantora.local"
        reg = client.post('/auth/register', json={
            'email': email,
            'password': 'quantora',
            'display_name': 'Stability Tester',
        })
        assert reg.status_code == 200, reg.text

        cfg = client.post('/automation/configure', json={
            'execution_mode': 'internal',
            'market_bias': 'neutral',
            'interval_seconds': 30,
            'broker_reconcile_enabled': True,
            'pnl_sync_enabled': True,
            'failure_pause_seconds': 60,
            'max_consecutive_failures': 3,
            'retry_on_failure': True,
            'max_retry_attempts': 2,
            'retry_backoff_seconds': 5,
        })
        assert cfg.status_code == 200, cfg.text

        started = client.post('/automation/start', json={
            'execution_mode': 'internal',
            'market_bias': 'neutral',
            'interval_seconds': 30,
            'broker_reconcile_enabled': True,
            'pnl_sync_enabled': True,
            'failure_pause_seconds': 60,
            'max_consecutive_failures': 3,
            'retry_on_failure': True,
            'max_retry_attempts': 2,
            'retry_backoff_seconds': 5,
        })
        assert started.status_code == 200, started.text

        health = client.get('/automation/health')
        assert health.status_code == 200, health.text

        metrics = client.get('/automation/cycle-metrics')
        assert metrics.status_code == 200, metrics.text

        run_once = client.post('/automation/run-once', json={'force': True})
        assert run_once.status_code == 200, run_once.text

        recover = client.post('/automation/recover', json={'restart_worker': True, 'clear_failures': True, 'run_immediately': False})
        assert recover.status_code == 200, recover.text

        print('qnt30347 smoke test passed')


if __name__ == '__main__':
    run()
