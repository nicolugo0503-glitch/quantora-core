
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app


def run():
    with TestClient(app) as client:
        spec = client.get('/openapi.json')
        assert spec.status_code == 200, spec.text
        paths = spec.json().get('paths', {})
        assert '/execution-optimization/status' in paths
        assert '/execution-optimization/plan' in paths
        assert '/execution-optimization/route' in paths

        email = f"execopt-{uuid.uuid4().hex[:8]}@quantora.local"
        reg = client.post('/auth/register', json={'email': email, 'password': 'quantora', 'display_name': 'Execution Optimizer Tester'})
        assert reg.status_code == 200, reg.text

        cap = client.post('/allocator/operator-capital/set', json={'allocated_capital': 15000})
        assert cap.status_code == 200, cap.text

        plan = client.post('/execution-optimization/plan', json={
            'symbol': 'AAPL',
            'side': 'buy',
            'qty': 25,
            'order_type': 'market',
            'execution_mode': 'paper',
            'urgency': 'balanced',
            'max_slippage_bps': 25,
            'strategy_name': 'AAPL Execution Test',
        })
        assert plan.status_code == 200, plan.text
        payload = plan.json()
        assert payload.get('symbol') == 'AAPL'
        assert payload.get('recommended_order_type') in ('market', 'limit')

        routed = client.post('/execution-optimization/route', json={
            'symbol': 'AAPL',
            'side': 'buy',
            'qty': 0.05,
            'order_type': 'market',
            'execution_mode': 'paper',
            'urgency': 'balanced',
            'max_slippage_bps': 30,
            'strategy_name': 'AAPL Execution Test',
            'governance_approved': False,
        })
        assert routed.status_code == 200, routed.text
        routed_json = routed.json()
        assert routed_json.get('status') in ('submitted', 'held')
        if routed_json.get('status') == 'submitted':
            assert routed_json.get('order', {}).get('optimizer_route') is True

        status = client.get('/execution-optimization/status')
        assert status.status_code == 200, status.text
        assert 'optimizer' in status.json()

        print('qnt30349 smoke test passed')


if __name__ == '__main__':
    run()
