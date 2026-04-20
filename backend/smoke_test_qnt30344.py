from backend.app.main import default_operator_state, evaluate_risk_state, enforce_risk_guard, default_risk_engine

state = default_operator_state('operator_test','Test')
state['risk_engine'] = default_risk_engine()
state['capital_source'] = {'mode':'internal','provider':'alpaca'}
state['allocator_caps']['operator'] = {'operator_id':'operator_test','allocated_capital':1000.0,'status':'FUNDED','updated_at':'now'}
state['orders'] = {'orders': []}
view = evaluate_risk_state(state)
assert 'totals' in view
state['risk_engine']['max_notional_per_trade'] = 20.0
blocked = False
try:
    enforce_risk_guard(state, 'AAPL', 'buy', 1, 'internal')
except Exception:
    blocked = True
assert blocked, 'expected max notional per trade to block 1 share of AAPL'
print('QNT30344 smoke test passed')
