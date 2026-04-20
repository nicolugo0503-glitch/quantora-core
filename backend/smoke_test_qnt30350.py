
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app

def run():
    with TestClient(app) as client:
        spec = client.get('/openapi.json')
        assert spec.status_code == 200, spec.text
        paths = spec.json().get('paths', {})
        assert '/governance/status' in paths
        assert '/governance/policy/simulate' in paths
        assert '/governance/enforcement/evaluate' in paths
        assert '/governance/approvals/aging' in paths

        admin_email = 'admin@quantora.local'
        reg = client.post('/auth/register', json={'email': admin_email, 'password': 'quantora', 'display_name': 'Governance Admin'})
        if reg.status_code not in (200, 409):
            raise AssertionError(reg.text)
        if reg.status_code == 409:
            login = client.post('/auth/login', json={'email': admin_email, 'password': 'quantora'})
            assert login.status_code == 200, login.text

        sim = client.post('/governance/policy/simulate', json={
            'event_type': 'live_order',
            'amount': 3500,
            'interval_seconds': 120,
            'qty': 15,
            'estimated_slippage_bps': 42,
            'execution_mode': 'live',
            'max_active_strategies': 4,
        })
        assert sim.status_code == 200, sim.text
        sim_json = sim.json()
        assert sim_json.get('event_type') == 'live_order'
        assert len(sim_json.get('breaches', [])) >= 1

        cap = client.post('/admin/operator-capital/set', json={'operator_id': 'operator_F5E2C5BA', 'allocated_capital': 12000})
        assert cap.status_code == 200, cap.text
        cap_json = cap.json()
        assert cap_json.get('status') in ('set', 'approval_required')

        enf = client.post('/governance/enforcement/evaluate', json={'operator_id': 'operator_F5E2C5BA', 'include_orders': True, 'include_approvals': True, 'include_risk': True})
        assert enf.status_code == 200, enf.text
        enf_json = enf.json()
        assert enf_json.get('operator_id') == 'operator_F5E2C5BA'
        assert enf_json.get('summary', {}).get('decision') in ('clear', 'hold')

        status = client.get('/governance/status')
        assert status.status_code == 200, status.text
        assert status.json().get('summary', {}).get('approval_pending_count') >= 0

        aging = client.get('/governance/approvals/aging')
        assert aging.status_code == 200, aging.text
        assert 'pending_count' in aging.json()

        print('qnt30350 smoke test passed')

if __name__ == '__main__':
    run()
