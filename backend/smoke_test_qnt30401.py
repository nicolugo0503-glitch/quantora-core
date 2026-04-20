from fastapi.testclient import TestClient
from autonomous_market_expansion_multi_asset_routing import app

client = TestClient(app)

assert client.get("/multi-asset-routing/status").status_code == 200

assert client.post("/multi-asset-routing/instruments/upsert", json={
    "instruments": [
        {"symbol":"AAPL","asset_class":"equities","venue_preferences":["alpaca"],"liquidity_score":0.92,"execution_quality":0.90,"enabled":True},
        {"symbol":"BTCUSD","asset_class":"crypto","venue_preferences":["binance","alpaca"],"liquidity_score":0.95,"execution_quality":0.88,"enabled":True},
        {"symbol":"EURUSD","asset_class":"forex","venue_preferences":["ibkr"],"liquidity_score":0.89,"execution_quality":0.84,"enabled":True}
    ]
}).status_code == 200

route = client.post("/multi-asset-routing/route", json={
    "symbol": "BTCUSD",
    "asset_class": "crypto",
    "side": "buy",
    "qty": 1,
    "urgency": "normal"
})
assert route.status_code == 200
assert route.json()["status"] == "ok"

exp = client.post("/multi-asset-routing/expand", json={
    "asset_class": "forex",
    "enable": True,
    "reason": "market expansion pilot",
    "operator_id": "governance-admin"
})
assert exp.status_code == 200

route_fx = client.post("/multi-asset-routing/route", json={
    "symbol": "EURUSD",
    "asset_class": "forex",
    "side": "buy",
    "qty": 1000,
    "urgency": "normal"
})
assert route_fx.status_code == 200

print("QNT30401 smoke test passed")
