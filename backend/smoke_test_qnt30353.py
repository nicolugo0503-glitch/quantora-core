
from venue_adapter_framework import (
    default_venue_adapter_state,
    venue_adapter_state_view,
    normalize_symbol,
    prepare_order_schema,
    market_data_snapshot,
    venue_register,
    venue_adapter_summary,
)

def run():
    state = venue_adapter_state_view({"venue_adapter_framework": default_venue_adapter_state()})
    a = normalize_symbol(state, canonical_symbol="BTCUSD", target_market="crypto", venue_id="binance")
    assert a["normalized_symbol"] == "BTC/USD"
    b = prepare_order_schema(state, venue_id="alpaca", symbol="AAPL", side="buy", qty=5, order_type="limit", price=180.25)
    assert "qty" in b["normalized_order"]
    c = market_data_snapshot(state, symbol="AAPL", market="equities", venue_id="alpaca")
    assert c["snapshot"]["bid"] < c["snapshot"]["ask"]
    d = venue_register(state, venue_id="kraken", asset_classes=["crypto"], latency_ms=31, status="standby")
    assert d["venue"]["venue_id"] == "kraken"
    s = venue_adapter_summary(state)
    assert s["venues_total"] >= 1
    print("QNT30353 smoke test passed")

if __name__ == "__main__":
    run()
