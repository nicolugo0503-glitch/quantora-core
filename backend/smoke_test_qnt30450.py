from backend.qnt30450_multi_broker_execution_fabric import build_multi_broker_package

pkg = build_multi_broker_package(
    brokers=[{"id":"b1","broker_name":"alpaca","broker_type":"execution","status":"active","latency_ms":80}],
    routes=[{"id":"r1","route_name":"US Equities","symbol_scope":"US_EQ","primary_broker":"alpaca","secondary_broker":"ibkr","status":"active"}],
    executions=[{"id":"e1","broker_name":"alpaca","symbol":"AAPL","side":"buy","notional_amount":5000,"status":"filled"}],
    failovers=[{"id":"f1","route_name":"US Equities","from_broker":"alpaca","to_broker":"ibkr","reason":"latency spike","status":"triggered"}],
)
assert pkg["summary"]["brokers_connected"] == 1
assert pkg["summary"]["routes_active"] == 1
assert pkg["summary"]["fabric_score"] >= 60
print("QNT30450 smoke test passed")
