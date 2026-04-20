from backend.app.qnt30703_live_broker_safety_layer_router import _bootstrap_demo_for_email, _summary_for_email, _evaluate_trade_for_email

EMAIL = 'operator@quantora.test'

summary = _bootstrap_demo_for_email(EMAIL)
assert summary['mission'] == 'QNT30703'
assert summary['safety_layer_status']['posture'] in {'SAFE', 'CONSTRAINED', 'BLOCKED'}

trade = _evaluate_trade_for_email(EMAIL, {
    'strategy_id': 'alpha_core',
    'symbol': 'AAPL',
    'side': 'buy',
    'qty': 50,
    'price': 190,
    'stop_loss': 186,
    'take_profit': 202,
})
assert trade['approved'] is True, trade
assert trade['violations'] == [], trade

blocked = _evaluate_trade_for_email(EMAIL, {
    'strategy_id': 'alpha_core',
    'symbol': 'SPY',
    'side': 'buy',
    'qty': 800,
    'price': 540,
})
assert blocked['approved'] is False
assert blocked['violations']
print('QNT30703 smoke test passed')
