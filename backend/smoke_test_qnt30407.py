from fastapi.testclient import TestClient
from unified_quantora_runtime_orchestrator import app

client = TestClient(app)

assert client.get("/runtime-orchestrator/status").status_code == 200
assert client.post("/runtime-orchestrator/module/set?module=execution&status=online&health=green").status_code == 200
assert client.post("/runtime-orchestrator/system/set?global_mode=autonomous&risk_state=safe&capital_state=deployable&broker_state=paper_connected").status_code == 200
assert client.post("/runtime-orchestrator/event/publish?topic=test.topic&message=hello").status_code == 200
assert client.post("/runtime-orchestrator/demo/run").status_code == 200
assert client.get("/runtime-orchestrator/event-bus").status_code == 200
print("QNT30407 smoke test passed")
