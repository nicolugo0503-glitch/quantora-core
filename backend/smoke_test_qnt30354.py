
from real_venue_connectors import (
    connector_upsert,
    default_execution_bus_state,
    execution_bus_state_view,
    execution_bus_summary,
    record_ack,
    record_fill,
    submit_intent,
)

def main():
    bus = execution_bus_state_view(default_execution_bus_state())
    connector_upsert(bus, connector_id='ibkr_paper', venue_id='ibkr', market='equities', mode='paper', latency_ms=29, reliability_score=99.4)
    submitted = submit_intent(bus, symbol='AAPL', side='buy', qty=3, market='equities', execution_mode='paper', urgency='balanced', order_type='market')
    assert submitted['status'] == 'submitted', submitted
    order_id = submitted['order_id']
    ack = record_ack(bus, order_id=order_id, ack_status='accepted', ack_latency_ms=19)
    assert ack['status'] == 'ok', ack
    fill = record_fill(bus, order_id=order_id, filled_qty=3, avg_fill_price=181.42, fill_latency_ms=63)
    assert fill['status'] == 'ok', fill
    summary = execution_bus_summary(bus)
    assert summary['bus_metrics']['orders_submitted'] >= 1, summary
    assert summary['bus_metrics']['acks_received'] >= 1, summary
    assert summary['bus_metrics']['fills_received'] >= 1, summary
    print('QNT30354 smoke test passed')

if __name__ == '__main__':
    main()
