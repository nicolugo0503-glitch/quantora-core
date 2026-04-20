
from fastapi.testclient import TestClient
from control_tower import app

c=TestClient(app)
assert c.get("/control-tower/status").status_code==200
assert c.post("/control-tower/alert",params={"message":"test"}).status_code==200
assert c.post("/control-tower/decision",params={"summary":"ok"}).status_code==200
print("QNT30405 OK")
