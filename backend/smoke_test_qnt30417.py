from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def run():
    r = client.get('/auth/me')
    assert r.status_code == 200
    r = client.get('/billing/subscription-status')
    assert r.status_code == 200
    data = r.json()
    assert data['billing']['plan'] in ('free', 'pro', 'institutional')
    r = client.post('/billing/create-checkout-session', json={'plan': 'pro'})
    assert r.status_code == 200
    r = client.post('/billing/webhook', json={'event_type': 'invoice.paid', 'operator_id': data['operator_id'], 'plan': 'institutional', 'subscription_status': 'active'})
    assert r.status_code == 200
    r = client.post('/broker-routing/submit', json={'symbol': 'AAPL', 'side': 'buy', 'qty': 1, 'execution_mode': 'live', 'governance_approved': True})
    assert r.status_code in (200, 400, 402)
    return {'status': 'ok'}

if __name__ == '__main__':
    print(run())
