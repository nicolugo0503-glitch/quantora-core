from fastapi.testclient import TestClient
from identity_auth_multitenant import app

client = TestClient(app)

assert client.get("/identity/status").status_code == 200

assert client.post("/identity/tenant/create", json={
    "tenant_id": "tenant-001",
    "tenant_name": "Quantora Client One",
    "plan": "pro"
}).status_code == 200

assert client.post("/identity/user/create", json={
    "user_id": "user-001",
    "tenant_id": "tenant-001",
    "full_name": "Client Admin",
    "email": "admin@example.com",
    "password": "quantora123",
    "role": "owner"
}).status_code == 200

login = client.post("/identity/login", json={
    "tenant_id": "tenant-001",
    "email": "admin@example.com",
    "password": "quantora123"
})
assert login.status_code == 200
token = login.json()["session"]["session_token"]

check = client.post("/identity/access/check", json={
    "session_token": token,
    "permission": "trading.write"
})
assert check.status_code == 200
assert check.json()["status"] == "allowed"

assert client.post("/identity/api-key/create", json={
    "user_id": "user-001",
    "tenant_id": "tenant-001",
    "label": "primary",
    "scopes": ["trading.read", "trading.write"]
}).status_code == 200

assert client.get("/identity/tenant/tenant-001/dashboard").status_code == 200

print("QNT30388 smoke test passed")
