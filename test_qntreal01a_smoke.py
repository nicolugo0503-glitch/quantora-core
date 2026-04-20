from backend.app.qntreal01a_operator_cockpit_router import operator_health, operator_summary


def test_operator_health_and_summary():
    health = operator_health()
    summary = operator_summary()
    assert health['status'] == 'ok'
    assert summary['status'] == 'ok'
    assert 'capital' in summary
    assert 'execution' in summary
    assert 'risk' in summary
