import uuid
from fastapi.testclient import TestClient
from backend.app.main import app


def run():
    with TestClient(app) as client:
        spec = client.get('/openapi.json')
        assert spec.status_code == 200, spec.text
        paths = spec.json().get('paths', {})
        assert '/multi-strategy/status' in paths
        assert '/multi-strategy/optimize' in paths
        assert '/multi-strategy/rebalance' in paths

        email = f"multi-{uuid.uuid4().hex[:8]}@quantora.local"
        reg = client.post('/auth/register', json={'email': email, 'password': 'quantora', 'display_name': 'Multi Strategy Tester'})
        assert reg.status_code == 200, reg.text

        cap = client.post('/allocator/operator-capital/set', json={'allocated_capital': 10000})
        assert cap.status_code == 200, cap.text

        strategies = [
            {'name': 'AAPL Momentum', 'symbol': 'AAPL', 'side': 'buy', 'default_qty': 2, 'enabled': True, 'capital_limit': 2000, 'execution_mode': 'inherit'},
            {'name': 'TSLA Mean Revert', 'symbol': 'TSLA', 'side': 'buy', 'default_qty': 1, 'enabled': True, 'capital_limit': 1500, 'execution_mode': 'inherit'},
            {'name': 'MSFT Trend', 'symbol': 'MSFT', 'side': 'buy', 'default_qty': 1, 'enabled': False, 'capital_limit': 1000, 'execution_mode': 'inherit'},
        ]
        ids = []
        for payload in strategies:
            r = client.post('/strategies/register', json=payload)
            assert r.status_code == 200, r.text
            ids.append(r.json()['strategy']['strategy_id'])

        cycle = client.post('/strategy-engine/run-cycle', json={'market_bias': 'bullish', 'execution_mode': 'internal'})
        assert cycle.status_code == 200, cycle.text

        status = client.get('/multi-strategy/status?max_active_strategies=2&market_bias=bullish')
        assert status.status_code == 200, status.text
        status_json = status.json()
        assert len(status_json.get('rankings', [])) >= 3

        optimized = client.post('/multi-strategy/optimize', json={
            'max_active_strategies': 2,
            'min_score_to_enable': 45,
            'pause_below_score': 30,
            'market_bias': 'bullish',
            'rebalance_capital': True,
        })
        assert optimized.status_code == 200, optimized.text

        rebalanced = client.post('/multi-strategy/rebalance', json={'max_active_strategies': 2, 'market_bias': 'bullish'})
        assert rebalanced.status_code == 200, rebalanced.text

        print('qnt30348 smoke test passed')


if __name__ == '__main__':
    run()
