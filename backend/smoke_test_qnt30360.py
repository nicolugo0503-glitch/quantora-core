from policy_simulator import default_policy_simulator_state, simulate_policy, compile_pretrade_approval

state = default_policy_simulator_state()
res = simulate_policy(state, action_type='order_submit', market='equities', symbol='AAPL', qty=200, price=190, execution_mode='live', estimated_slippage_bps=12, net_exposure_usd=50000)
assert res['simulation']['verdict'] in ('approval_required', 'blocked', 'approved')
res2 = compile_pretrade_approval(state, simulation=res['simulation'], requested_by='nicolugo0503@gmail.com', operator_id='operator_demo')
assert res2['approval_request']['simulation_id'] == res['simulation']['simulation_id']
print('QNT30360 smoke test passed')
