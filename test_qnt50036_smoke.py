from backend.app.cross_border_service_routing.engine import CrossBorderServiceRoutingEngine
from backend.app.cross_border_service_routing.state_store import save_state, default_state


def main():
    save_state(default_state())
    engine = CrossBorderServiceRoutingEngine()
    engine.sync_context({'source': 'smoke'})
    reg = engine.register_route_case({
        'operator': 'smoke',
        'source_region': 'EMEA',
        'destination_region': 'AMER',
        'source_jurisdiction': 'uk',
        'destination_jurisdiction': 'us',
        'service_channels': ['ops', 'compliance'],
        'route_notional': 1000.0,
        'route_limit': 2000.0,
        'partition_event_id': 'partition_event_smoke',
    })
    route_case_id = reg['route_case']['route_case_id']
    app = engine.approve_route({'operator': 'smoke', 'route_case_id': route_case_id, 'approved_notional': 1200.0, 'boundary_clearance': True})
    assert app['status'] == 'approved'
    exe = engine.execute_route({'operator': 'smoke', 'route_case_id': route_case_id, 'routed_channel_count': 2})
    assert exe['status'] == 'executed'
    clo = engine.close_route_case({'operator': 'smoke', 'route_case_id': route_case_id})
    assert clo['status'] == 'closed'
    print('QNT50036 smoke passed')


if __name__ == '__main__':
    main()
