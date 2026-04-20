
from fastapi.testclient import TestClient
from backend.app.main import app


def run():
    with TestClient(app) as client:
        spec = client.get('/openapi.json')
        assert spec.status_code == 200, spec.text
        paths = spec.json().get('paths', {})
        for path in [
            '/autonomy/status',
            '/autonomy/evaluate',
            '/autonomy/transition',
            '/autonomy/delegation/update',
            '/autonomy/run-cycle',
        ]:
            assert path in paths, path

        admin_email = 'admin@quantora.local'
        reg = client.post('/auth/register', json={'email': admin_email, 'password': 'quantora', 'display_name': 'Autonomy Admin'})
        if reg.status_code not in (200, 409):
            raise AssertionError(reg.text)
        if reg.status_code == 409:
            login = client.post('/auth/login', json={'email': admin_email, 'password': 'quantora'})
            assert login.status_code == 200, login.text

        delegation = client.post('/autonomy/delegation/update', json={
            'operator_id': 'operator_F5E2C5BA',
            'tier': 'manager',
            'max_live_notional': 5000,
            'allow_live_orders': True,
            'allow_strategy_mutations': True,
        })
        assert delegation.status_code == 200, delegation.text
        assert delegation.json().get('delegation', {}).get('tier') == 'manager'

        evaluate = client.post('/autonomy/evaluate', json={
            'operator_id': 'operator_F5E2C5BA',
            'execution_mode': 'paper',
            'market_bias': 'neutral',
        })
        assert evaluate.status_code == 200, evaluate.text
        assert 'recommended_mode' in evaluate.json().get('summary', {})

        transition = client.post('/autonomy/transition', json={
            'operator_id': 'operator_F5E2C5BA',
            'target_mode': 'constrained_autonomy',
        })
        assert transition.status_code in (200, 400), transition.text

        status = client.get('/autonomy/status')
        assert status.status_code == 200, status.text
        assert status.json().get('summary', {}).get('current_mode') in ('supervised', 'constrained_autonomy', 'delegated_autonomy', 'locked')

        run_cycle = client.post('/autonomy/run-cycle', json={
            'operator_id': 'operator_F5E2C5BA',
            'execution_mode': 'paper',
            'market_bias': 'neutral',
            'force': True,
        })
        assert run_cycle.status_code in (200, 400), run_cycle.text
        print('qnt30351 smoke test passed')


if __name__ == '__main__':
    run()
