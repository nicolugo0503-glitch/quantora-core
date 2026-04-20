from backend.app.allocation.engine import AllocationEngine
from backend.app.strategy_deployment.engine import StrategyDeploymentEngine


def main():
    alloc = AllocationEngine()
    plan = alloc.recommend({
        'capital': 1800000,
        'regime': 'bull',
        'liquidity_state': 'normal',
        'max_strategy_weight': 0.35,
    })
    alloc.approve({'approver': 'smoke_test', 'notes': 'qnt50003 dependency ready', 'plan': plan})

    engine = StrategyDeploymentEngine()
    deploy_plan = engine.evaluate({
        'regime': 'bull',
        'liquidity_state': 'normal',
        'max_concurrent_strategies': 2,
    })
    assert deploy_plan['mission'] == 'QNT50003'
    assert deploy_plan['status'] == 'proposed'
    assert deploy_plan['deployments']
    approved = engine.deploy({'approver': 'smoke_test', 'notes': 'deployment validated', 'plan': deploy_plan})
    assert approved['status'] == 'approved'
    assert approved['release_queue']
    summary = engine.summary()
    assert summary['mission'] == 'QNT50003'
    print('QNT50003 smoke passed')


if __name__ == '__main__':
    main()
