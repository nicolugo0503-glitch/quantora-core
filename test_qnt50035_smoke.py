from backend.app.multi_region_service_partition.engine import MultiRegionServicePartitionEngine
from backend.app.multi_region_service_partition.state_store import save_state, default_state


def main():
    save_state(default_state())
    engine = MultiRegionServicePartitionEngine()
    engine.sync_context({'source': 'smoke'})
    reg = engine.register_expansion_case({
        'operator': 'smoke',
        'region_name': 'EMEA',
        'jurisdictions': ['uk', 'eu'],
        'service_partitions': ['ops', 'compliance'],
        'regional_budget': 1000.0,
        'budget_limit': 2000.0,
    })
    expansion_case_id = reg['expansion_case']['expansion_case_id']
    app = engine.approve_partition({'operator': 'smoke', 'expansion_case_id': expansion_case_id, 'approved_budget': 1200.0})
    assert app['status'] == 'approved'
    exe = engine.execute_partition({'operator': 'smoke', 'expansion_case_id': expansion_case_id, 'jurisdiction_count': 2})
    assert exe['status'] == 'executed'
    clo = engine.close_expansion_case({'operator': 'smoke', 'expansion_case_id': expansion_case_id})
    assert clo['status'] == 'closed'
    print('QNT50035 smoke passed')


if __name__ == '__main__':
    main()
