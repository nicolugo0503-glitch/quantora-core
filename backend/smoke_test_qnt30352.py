from fastapi.testclient import TestClient
from backend.app.main import app


def run():
    with TestClient(app) as client:
        spec = client.get('/openapi.json')
        assert spec.status_code == 200, spec.text
        paths = spec.json().get('paths', {})
        for path in [
            '/broker-abstraction/status',
            '/broker-abstraction/router/evaluate',
            '/broker-abstraction/brokers/upsert',
            '/broker-abstraction/markets/upsert',
            '/broker-abstraction/portfolio/expand',
        ]:
            assert path in paths, path

        admin_email = 'admin@quantora.local'
        reg = client.post('/auth/register', json={'email': admin_email, 'password': 'quantora', 'display_name': 'Broker Admin'})
        if reg.status_code not in (200, 409):
            raise AssertionError(reg.text)
        if reg.status_code == 409:
            login = client.post('/auth/login', json={'email': admin_email, 'password': 'quantora'})
            assert login.status_code == 200, login.text

        status = client.get('/broker-abstraction/status')
        assert status.status_code == 200, status.text
        assert 'summary' in status.json(), status.text

        market = client.post('/broker-abstraction/markets/upsert', json={
            'market_id': 'options',
            'enabled': True,
            'symbols': ['SPY_CALL', 'QQQ_CALL'],
            'default_order_type': 'limit',
            'session_profile': 'cash',
            'risk_multiplier': 1.6,
        })
        assert market.status_code == 200, market.text
        assert market.json()['market']['market_id'] == 'options'

        broker = client.post('/broker-abstraction/brokers/upsert', json={
            'broker_id': 'sim-options',
            'enabled': True,
            'markets': ['options'],
            'live_supported': False,
            'paper_supported': True,
            'base_fee_bps': 2.5,
            'latency_ms': 80,
            'reliability_score': 0.97,
            'slippage_penalty_bps': 2.1,
            'notes': 'options sandbox',
        })
        assert broker.status_code == 200, broker.text
        assert broker.json()['broker']['broker_id'] == 'sim-options'

        route = client.post('/broker-abstraction/router/evaluate', json={
            'market': 'crypto',
            'symbol': 'BTCUSD',
            'side': 'buy',
            'qty': 0.1,
            'execution_mode': 'paper',
            'urgency': 'balanced',
        })
        assert route.status_code == 200, route.text
        assert route.json().get('status') == 'ok', route.text
        assert route.json().get('selected_broker', {}).get('broker_id') in ('alpaca', 'sim-crypto')

        expand = client.post('/broker-abstraction/portfolio/expand', json={
            'allocations': {'equities': 55, 'crypto': 20, 'futures': 15, 'forex': 10},
            'target_markets': ['equities', 'crypto', 'futures', 'forex'],
        })
        assert expand.status_code == 200, expand.text
        assert expand.json().get('result', {}).get('allocation_total') == 100.0
        print('qnt30352 smoke test passed')


if __name__ == '__main__':
    run()
