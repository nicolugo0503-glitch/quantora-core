from fastapi.testclient import TestClient
from global_risk_mesh_capital_defense import app
client=TestClient(app)
assert client.get("/global-risk-mesh/status").status_code==200
assert client.post("/global-risk-mesh/node/update",json={"node":"market_stress","value":0.78,"threshold":0.70}).status_code==200
assert client.post("/global-risk-mesh/node/update",json={"node":"execution_drift","value":0.18,"threshold":0.15}).status_code==200
assert client.post("/global-risk-mesh/policies/update",json={"risk_score_alert":0.50,"risk_score_throttle":0.65,"risk_score_freeze":0.85,"reserve_raise_ratio":0.18,"capital_throttle_ratio":0.55}).status_code==200
ev=client.post("/global-risk-mesh/defense/evaluate"); assert ev.status_code==200 and ev.json()["status"]=="ok"
assert client.get("/global-risk-mesh/defense-actions").status_code==200
assert client.get("/global-risk-mesh/events").status_code==200
print("QNT30403 smoke test passed")
