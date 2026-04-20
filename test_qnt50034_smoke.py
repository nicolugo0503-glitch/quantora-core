from backend.app.multi_vehicle_shared_services.engine import MultiVehicleSharedServicesEngine
from backend.app.multi_vehicle_shared_services.state_store import save_state, default_state


def main():
    save_state(default_state())
    engine = MultiVehicleSharedServicesEngine()
    engine.sync_context({'source': 'smoke'})
    reg = engine.register_service_model({
        'operator': 'smoke',
        'service_name': 'Shared Ops',
        'supported_vehicle_types': ['fund','spv'],
        'annual_budget': 1000.0,
        'service_scope': 'ops and finance',
    })
    service_model_id = reg['service_model']['service_model_id']
    app = engine.approve_service_model({'operator': 'smoke', 'service_model_id': service_model_id, 'approved_budget': 1200.0})
    assert app['status'] == 'approved'
    exe = engine.execute_service_model({'operator': 'smoke', 'service_model_id': service_model_id, 'vehicle_count': 2})
    assert exe['status'] == 'executed'
    clo = engine.close_service_model({'operator': 'smoke', 'service_model_id': service_model_id})
    assert clo['status'] == 'closed'
    print('QNT50034 smoke passed')


if __name__ == '__main__':
    main()
