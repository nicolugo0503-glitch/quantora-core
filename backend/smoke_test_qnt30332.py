import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app.main import app


def main():
    with TestClient(app) as client:
        client.post('/allocator/operator-capital/set', json={'allocated_capital': 10000})
        reg = client.post('/strategies/register', json={
            'name': 'QNT30332 Smoke Strategy',
            'symbol': 'AAPL',
            'side': 'buy',
            'default_qty': 1,
            'enabled': True,
            'capital_limit': 5000,
            'execution_mode': 'inherit',
        }).json()
        strategy = reg.get('strategy', {})
        strategy_id = strategy.get('strategy_id')
        if strategy_id:
            client.post('/strategies/lifecycle', json={'strategy_id': strategy_id, 'action': 'start'})

        client.post('/automation/start', json={
            'execution_mode': 'internal',
            'market_bias': 'bullish',
            'interval_seconds': 5,
            'broker_reconcile_enabled': True,
            'pnl_sync_enabled': True,
            'failure_pause_seconds': 15,
            'max_consecutive_failures': 2,
        })
        tick = client.post('/automation/tick', json={'force': True}).json()
        status = client.get('/automation/status').json()
        orders = client.get('/execution/orders').json()
        print({
            'automation_tick': tick.get('status'),
            'automation_cycles': status.get('automation', {}).get('operator', {}).get('cycle_count'),
            'orders_count': orders.get('count'),
            'last_engine_status': status.get('workspace', {}).get('execution_engine', {}).get('last_cycle_status'),
        })


if __name__ == '__main__':
    main()
