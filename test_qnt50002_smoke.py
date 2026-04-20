from backend.app.allocation.engine import AllocationEngine


def main():
    engine = AllocationEngine()
    plan = engine.recommend({
        'capital': 1500000,
        'regime': 'neutral',
        'liquidity_state': 'normal',
        'max_strategy_weight': 0.35,
    })
    assert plan['mission'] == 'QNT50002'
    assert plan['status'] == 'proposed'
    assert plan['allocations']
    approved = engine.approve({'approver': 'smoke_test', 'notes': 'validated in smoke'})
    assert approved['status'] == 'approved'
    handoff = engine.execution_handoff()
    assert handoff['handoff']['tickets']
    print('QNT50002 smoke passed')


if __name__ == '__main__':
    main()
