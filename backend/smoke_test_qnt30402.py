from fastapi.testclient import TestClient
from cross_market_portfolio_intelligence import app

client = TestClient(app)

assert client.get("/cross-market-intelligence/status").status_code == 200

assert client.post("/cross-market-intelligence/exposure/update", json={
    "market": "equities",
    "notional": 450000,
    "pnl": 15000,
    "risk_score": 0.43
}).status_code == 200

assert client.post("/cross-market-intelligence/exposure/update", json={
    "market": "crypto",
    "notional": 260000,
    "pnl": 9000,
    "risk_score": 0.61
}).status_code == 200

assert client.post("/cross-market-intelligence/correlations/update", json={
    "pairs": {
        "equities:crypto": 0.46,
        "equities:forex": 0.21,
        "crypto:forex": 0.18
    }
}).status_code == 200

assert client.post("/cross-market-intelligence/signal", json={
    "source_market": "crypto",
    "target_market": "equities",
    "signal_type": "risk_spillover",
    "confidence": 0.78,
    "message": "Crypto volatility spilling into equity beta names"
}).status_code == 200

assert client.post("/cross-market-intelligence/rebalance/recommend").status_code == 200
assert client.get("/cross-market-intelligence/rebalance-suggestions").status_code == 200

print("QNT30402 smoke test passed")
