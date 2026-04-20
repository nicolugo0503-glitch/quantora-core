import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

roles = client.get('/workspace/roles')
assert roles.status_code == 200, roles.text
assert roles.json().get('mission') == 'QNT30422'

orgs = client.get('/workspace/organizations')
assert orgs.status_code == 200, orgs.text
payload = orgs.json()
assert payload.get('mission') == 'QNT30422'
assert isinstance(payload.get('organizations'), list)
assert payload.get('organizations')

ctx = client.get('/workspace/context')
assert ctx.status_code == 200, ctx.text
ctx_payload = ctx.json()
assert ctx_payload.get('mission') == 'QNT30422'
assert ctx_payload.get('organization')

create = client.post('/workspace/organizations/create', json={'name': 'Atlas Capital', 'plan': 'institutional', 'initial_balance': 250000})
assert create.status_code == 200, create.text
new_org_id = create.json().get('organization_id')
assert new_org_id

switch = client.post('/workspace/switch', json={'organization_id': new_org_id})
assert switch.status_code == 200, switch.text

member = client.post('/workspace/members/add', json={'organization_id': new_org_id, 'user_email': 'analyst@atlas.capital', 'role': 'analyst'})
assert member.status_code == 200, member.text

accounts = client.get('/workspace/accounts')
assert accounts.status_code == 200, accounts.text
assert accounts.json().get('organization', {}).get('id') == new_org_id

print('QNT30422 smoke test passed')
