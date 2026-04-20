
import math
from datetime import datetime, timezone

PRICE_BOOK = {
    "AAPL": 180.0,
    "TSLA": 175.0,
    "SPY": 510.0,
    "NVDA": 910.0,
    "MSFT": 420.0,
    "AMZN": 185.0,
    "META": 505.0,
}
LIQUIDITY_PROFILES = {
    "SPY": {"adv": 85_000_000, "spread_bps": 1.0, "volatility": 0.9},
    "AAPL": {"adv": 55_000_000, "spread_bps": 1.5, "volatility": 1.0},
    "MSFT": {"adv": 30_000_000, "spread_bps": 1.8, "volatility": 0.9},
    "NVDA": {"adv": 42_000_000, "spread_bps": 2.8, "volatility": 1.5},
    "AMZN": {"adv": 28_000_000, "spread_bps": 2.1, "volatility": 1.1},
    "META": {"adv": 20_000_000, "spread_bps": 2.2, "volatility": 1.2},
    "TSLA": {"adv": 75_000_000, "spread_bps": 3.4, "volatility": 1.7},
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def default_execution_optimizer():
    return {
        "enabled": True,
        "last_plan_at": None,
        "last_route_at": None,
        "last_symbol": None,
        "last_decision": "idle",
        "last_order_type": None,
        "plans_generated": 0,
        "orders_optimized": 0,
        "orders_held": 0,
        "avg_estimated_slippage_bps": 0.0,
        "saved_slippage_bps": 0.0,
        "telemetry": [],
    }


def execution_optimizer_state(state):
    engine = state.setdefault("execution_engine", {})
    opt = engine.setdefault("execution_optimizer", default_execution_optimizer())
    for k, v in default_execution_optimizer().items():
        opt.setdefault(k, v)
    return opt


def _price(symbol):
    return float(PRICE_BOOK.get((symbol or '').upper(), 100.0))


def _profile(symbol):
    return LIQUIDITY_PROFILES.get((symbol or '').upper(), {"adv": 8_000_000, "spread_bps": 4.0, "volatility": 1.25})


def build_execution_plan(state, *, symbol, side='buy', qty=1.0, order_type='market', execution_mode='paper', urgency='balanced', max_slippage_bps=35.0, strategy_id=None, strategy_name=None, risk_state=None):
    symbol = (symbol or 'AAPL').upper()
    side = (side or 'buy').lower()
    order_type = (order_type or 'market').lower()
    execution_mode = (execution_mode or 'paper').lower()
    urgency = (urgency or 'balanced').lower()
    qty = max(float(qty or 0.0), 0.0)
    max_slippage_bps = max(float(max_slippage_bps or 0.0), 1.0)
    price = _price(symbol)
    profile = _profile(symbol)
    adv = float(profile['adv'])
    participation = min(0.25, qty / max(adv, 1.0))
    urgency_mult = {'patient': 0.82, 'balanced': 1.0, 'aggressive': 1.28}.get(urgency, 1.0)
    spread = float(profile['spread_bps'])
    vol = float(profile['volatility'])
    estimated_slippage_bps = round(spread * urgency_mult + (math.sqrt(max(participation, 0.0)) * 250 * vol), 2)
    market_bps = round(estimated_slippage_bps + spread * 0.7, 2)
    limit_bps = round(max(spread * 0.75, estimated_slippage_bps * 0.72), 2)
    recommended_order_type = 'limit' if (market_bps > max_slippage_bps * 0.8 or urgency == 'patient') else order_type
    if order_type == 'limit':
        recommended_order_type = 'limit'
    if execution_mode == 'internal' and recommended_order_type == 'market' and estimated_slippage_bps > 10:
        recommended_order_type = 'limit'
    estimated_fill_price = price * (1 + (estimated_slippage_bps / 10000.0 if side == 'buy' else -(estimated_slippage_bps / 10000.0)))
    slices = 1
    if participation > 0.03:
        slices = 5
    elif participation > 0.01:
        slices = 3
    elif qty >= 100:
        slices = 2
    slice_qty = round(qty / max(slices, 1), 6)
    schedule = {
        'slices': slices,
        'slice_qty': slice_qty,
        'cadence_seconds': 0 if slices == 1 else (90 if urgency == 'aggressive' else 180 if urgency == 'balanced' else 300),
        'window': 'now' if slices == 1 else ('open_plus_15m' if urgency == 'aggressive' else 'session_vwap'),
    }
    decision = 'execute'
    hold_reason = None
    if estimated_slippage_bps > max_slippage_bps:
        decision = 'hold'
        hold_reason = f'estimated slippage {estimated_slippage_bps} bps exceeds max {round(max_slippage_bps, 2)} bps'
    if risk_state and (risk_state.get('status') not in ('SAFE', 'UNKNOWN')):
        decision = 'hold'
        hold_reason = 'risk engine not safe for optimized execution'
    expected_cost = round(price * qty * (estimated_slippage_bps / 10000.0), 2)
    return {
        'generated_at': now_iso(),
        'symbol': symbol,
        'side': side,
        'qty': round(qty, 6),
        'price_reference': round(price, 4),
        'execution_mode': execution_mode,
        'order_type': order_type,
        'recommended_order_type': recommended_order_type,
        'urgency': urgency,
        'strategy_id': strategy_id,
        'strategy_name': strategy_name,
        'liquidity_profile': {'adv': int(adv), 'spread_bps': spread, 'volatility': vol, 'participation_rate': round(participation, 6)},
        'estimated_slippage_bps': estimated_slippage_bps,
        'market_order_slippage_bps': market_bps,
        'limit_order_slippage_bps': limit_bps,
        'expected_fill_price': round(estimated_fill_price, 4),
        'expected_slippage_cost': expected_cost,
        'schedule': schedule,
        'decision': decision,
        'hold_reason': hold_reason,
        'recommended_qty': round(qty, 6),
        'tags': ['execution-optimized', f'urgency:{urgency}', f'slices:{slices}'],
    }


def record_execution_plan(state, plan):
    opt = execution_optimizer_state(state)
    opt['last_plan_at'] = plan.get('generated_at')
    opt['last_symbol'] = plan.get('symbol')
    opt['last_decision'] = plan.get('decision')
    opt['last_order_type'] = plan.get('recommended_order_type')
    opt['plans_generated'] = int(opt.get('plans_generated', 0)) + 1
    if plan.get('decision') == 'hold':
        opt['orders_held'] = int(opt.get('orders_held', 0)) + 1
    telemetry = list(opt.get('telemetry') or [])
    telemetry.insert(0, {
        'at': plan.get('generated_at'),
        'symbol': plan.get('symbol'),
        'decision': plan.get('decision'),
        'estimated_slippage_bps': plan.get('estimated_slippage_bps'),
        'recommended_order_type': plan.get('recommended_order_type'),
        'schedule': plan.get('schedule'),
    })
    opt['telemetry'] = telemetry[:50]
    prev_avg = float(opt.get('avg_estimated_slippage_bps') or 0.0)
    count = max(int(opt.get('plans_generated') or 1), 1)
    opt['avg_estimated_slippage_bps'] = round((((count - 1) * prev_avg) + float(plan.get('estimated_slippage_bps') or 0.0)) / count, 2)
    return opt


def record_execution_result(state, plan, order):
    if not plan:
        return execution_optimizer_state(state)
    opt = execution_optimizer_state(state)
    opt['orders_optimized'] = int(opt.get('orders_optimized', 0)) + 1
    opt['last_route_at'] = now_iso()
    saved = max(0.0, float(plan.get('market_order_slippage_bps') or 0.0) - float(plan.get('estimated_slippage_bps') or 0.0))
    opt['saved_slippage_bps'] = round(float(opt.get('saved_slippage_bps') or 0.0) + saved, 2)
    telemetry = list(opt.get('telemetry') or [])
    if telemetry:
        telemetry[0]['order_id'] = order.get('order_id')
        telemetry[0]['status'] = order.get('status')
    opt['telemetry'] = telemetry[:50]
    return opt
