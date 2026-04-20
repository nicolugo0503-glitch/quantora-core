
import uuid
from datetime import datetime, timezone

DEFAULT_CONNECTORS = {
    "alpaca_live": {
        "connector_id": "alpaca_live",
        "venue_id": "alpaca",
        "market": "equities",
        "mode": "live",
        "status": "active",
        "supports_order_types": ["market", "limit"],
        "supports_time_in_force": ["day", "gtc", "ioc"],
        "latency_ms": 42,
        "reliability_score": 99.2,
    },
    "alpaca_paper": {
        "connector_id": "alpaca_paper",
        "venue_id": "alpaca",
        "market": "equities",
        "mode": "paper",
        "status": "active",
        "supports_order_types": ["market", "limit"],
        "supports_time_in_force": ["day", "gtc"],
        "latency_ms": 18,
        "reliability_score": 99.8,
    },
    "binance_sim": {
        "connector_id": "binance_sim",
        "venue_id": "binance",
        "market": "crypto",
        "mode": "paper",
        "status": "standby",
        "supports_order_types": ["market", "limit"],
        "supports_time_in_force": ["gtc", "ioc", "fok"],
        "latency_ms": 27,
        "reliability_score": 98.9,
    },
}

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def default_execution_bus_state():
    return {
        "enabled": True,
        "last_updated_at": None,
        "last_submitted_at": None,
        "last_ack_at": None,
        "last_fill_at": None,
        "connectors": DEFAULT_CONNECTORS.copy(),
        "routing_preferences": {
            "equities": ["alpaca_live", "alpaca_paper"],
            "crypto": ["binance_sim"],
            "forex": [],
            "futures": [],
        },
        "bus_metrics": {
            "orders_submitted": 0,
            "acks_received": 0,
            "fills_received": 0,
            "rejects_received": 0,
            "avg_ack_latency_ms": 0.0,
            "avg_fill_latency_ms": 0.0,
        },
        "events": [],
        "active_orders": {},
    }

def execution_bus_state_view(data):
    merged = default_execution_bus_state()
    incoming = (data or {}).get('execution_bus', data or {})
    if isinstance(incoming, dict):
        for k, v in incoming.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
    return merged

def _push_event(state, event):
    state.setdefault('events', []).insert(0, event)
    state['events'] = state['events'][:250]

def connector_upsert(state, *, connector_id, venue_id, market='equities', mode='paper', status='active', order_types=None, tif_options=None, latency_ms=25, reliability_score=99.0):
    connector_id = (connector_id or '').strip().lower()
    if not connector_id:
        raise ValueError('connector_id required')
    connector = {
        'connector_id': connector_id,
        'venue_id': (venue_id or '').strip().lower() or connector_id,
        'market': (market or 'equities').strip().lower(),
        'mode': (mode or 'paper').strip().lower(),
        'status': (status or 'active').strip().lower(),
        'supports_order_types': list(order_types or ['market', 'limit']),
        'supports_time_in_force': list(tif_options or ['day', 'gtc']),
        'latency_ms': int(latency_ms or 25),
        'reliability_score': float(reliability_score or 99.0),
        'updated_at': now_iso(),
    }
    state.setdefault('connectors', {})[connector_id] = connector
    prefs = state.setdefault('routing_preferences', {})
    prefs.setdefault(connector['market'], [])
    if connector_id not in prefs[connector['market']]:
        prefs[connector['market']].append(connector_id)
    state['last_updated_at'] = now_iso()
    _push_event(state, {'timestamp': now_iso(), 'type': 'connector_upsert', 'connector_id': connector_id, 'market': connector['market'], 'mode': connector['mode']})
    return {'status': 'ok', 'connector': connector}

def route_intent(state, *, symbol, market='equities', execution_mode='paper', urgency='balanced', preferred_connector_id=None, qty=1.0, order_type='market'):
    market = (market or 'equities').lower()
    execution_mode = (execution_mode or 'paper').lower()
    candidates = []
    for connector_id in state.get('routing_preferences', {}).get(market, []):
        connector = state.get('connectors', {}).get(connector_id)
        if not connector or connector.get('status') != 'active':
            continue
        if connector.get('mode') != execution_mode:
            continue
        if order_type not in connector.get('supports_order_types', []):
            continue
        score = 100.0
        score -= float(connector.get('latency_ms') or 0) * (1.2 if urgency == 'aggressive' else 0.7)
        score += float(connector.get('reliability_score') or 0) * 0.3
        if preferred_connector_id and connector_id == preferred_connector_id:
            score += 8.0
        candidates.append((round(score, 2), connector))
    if not candidates:
        return {'status': 'no_route', 'reason': 'no active compatible connector', 'symbol': symbol, 'market': market, 'execution_mode': execution_mode}
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best = candidates[0]
    return {
        'status': 'ok',
        'route': {
            'symbol': symbol,
            'market': market,
            'execution_mode': execution_mode,
            'connector_id': best['connector_id'],
            'venue_id': best['venue_id'],
            'score': best_score,
            'estimated_ack_latency_ms': int(best.get('latency_ms') or 25),
            'estimated_fill_latency_ms': int((best.get('latency_ms') or 25) * (1.7 if urgency == 'aggressive' else 2.4)),
            'qty': round(float(qty or 0.0), 8),
            'order_type': order_type,
            'urgency': urgency,
        },
        'candidates': [
            {'connector_id': c['connector_id'], 'venue_id': c['venue_id'], 'score': s, 'latency_ms': c.get('latency_ms'), 'reliability_score': c.get('reliability_score')}
            for s, c in candidates[:5]
        ],
    }

def submit_intent(state, *, symbol, side, qty, market='equities', execution_mode='paper', urgency='balanced', order_type='market', tif='day', preferred_connector_id=None, strategy_id=None):
    routed = route_intent(state, symbol=symbol, market=market, execution_mode=execution_mode, urgency=urgency, preferred_connector_id=preferred_connector_id, qty=qty, order_type=order_type)
    if routed.get('status') != 'ok':
        return routed
    route = routed['route']
    order_id = f"bus_{uuid.uuid4().hex[:12]}"
    event = {
        'event_id': f"evt_{uuid.uuid4().hex[:10]}",
        'timestamp': now_iso(),
        'event_type': 'order_submitted',
        'order_id': order_id,
        'connector_id': route['connector_id'],
        'venue_id': route['venue_id'],
        'symbol': symbol,
        'side': (side or 'buy').lower(),
        'qty': round(float(qty or 0.0), 8),
        'market': market,
        'execution_mode': execution_mode,
        'order_type': order_type,
        'tif': tif,
        'strategy_id': strategy_id,
        'ack_status': 'pending',
        'fill_status': 'pending',
    }
    state.setdefault('active_orders', {})[order_id] = event.copy()
    state['last_submitted_at'] = now_iso()
    metrics = state.setdefault('bus_metrics', {})
    metrics['orders_submitted'] = int(metrics.get('orders_submitted') or 0) + 1
    _push_event(state, event)
    return {'status': 'submitted', 'order_id': order_id, 'route': route, 'event': event, 'candidates': routed.get('candidates', [])}

def record_ack(state, *, order_id, ack_status='accepted', venue_order_id=None, ack_latency_ms=None, message=None):
    active = state.setdefault('active_orders', {})
    order = active.get(order_id)
    if not order:
        return {'status': 'not_found', 'order_id': order_id}
    ack_latency_ms = int(ack_latency_ms if ack_latency_ms is not None else 25)
    order['ack_status'] = ack_status
    order['venue_order_id'] = venue_order_id or f"venue_{order_id[-8:]}"
    order['ack_latency_ms'] = ack_latency_ms
    order['ack_at'] = now_iso()
    order['message'] = message
    state['last_ack_at'] = now_iso()
    metrics = state.setdefault('bus_metrics', {})
    if str(ack_status).lower() == 'rejected':
        metrics['rejects_received'] = int(metrics.get('rejects_received') or 0) + 1
    else:
        metrics['acks_received'] = int(metrics.get('acks_received') or 0) + 1
    acks = max(int(metrics.get('acks_received') or 0), 1)
    metrics['avg_ack_latency_ms'] = round(((float(metrics.get('avg_ack_latency_ms') or 0.0) * (acks - 1)) + ack_latency_ms) / acks, 2)
    _push_event(state, {'timestamp': now_iso(), 'event_type': 'order_ack', 'order_id': order_id, 'ack_status': ack_status, 'venue_order_id': order['venue_order_id'], 'ack_latency_ms': ack_latency_ms, 'message': message})
    return {'status': 'ok', 'order': order}

def record_fill(state, *, order_id, filled_qty=None, avg_fill_price=None, fill_latency_ms=None, fill_status='filled'):
    active = state.setdefault('active_orders', {})
    order = active.get(order_id)
    if not order:
        return {'status': 'not_found', 'order_id': order_id}
    fill_latency_ms = int(fill_latency_ms if fill_latency_ms is not None else 60)
    order['fill_status'] = fill_status
    order['filled_qty'] = round(float(filled_qty if filled_qty is not None else order.get('qty') or 0.0), 8)
    order['avg_fill_price'] = float(avg_fill_price if avg_fill_price is not None else 100.0)
    order['fill_latency_ms'] = fill_latency_ms
    order['fill_at'] = now_iso()
    state['last_fill_at'] = now_iso()
    metrics = state.setdefault('bus_metrics', {})
    metrics['fills_received'] = int(metrics.get('fills_received') or 0) + 1
    fills = max(int(metrics.get('fills_received') or 0), 1)
    metrics['avg_fill_latency_ms'] = round(((float(metrics.get('avg_fill_latency_ms') or 0.0) * (fills - 1)) + fill_latency_ms) / fills, 2)
    _push_event(state, {'timestamp': now_iso(), 'event_type': 'order_fill', 'order_id': order_id, 'fill_status': fill_status, 'filled_qty': order['filled_qty'], 'avg_fill_price': order['avg_fill_price'], 'fill_latency_ms': fill_latency_ms})
    return {'status': 'ok', 'order': order}

def execution_bus_summary(state):
    connectors = state.get('connectors', {})
    active_orders = state.get('active_orders', {})
    by_market = {}
    for c in connectors.values():
        by_market[c.get('market', 'unknown')] = by_market.get(c.get('market', 'unknown'), 0) + 1
    return {
        'status': 'ok',
        'connectors_total': len(connectors),
        'markets_covered': sorted(by_market.keys()),
        'coverage_counts': by_market,
        'active_orders': len(active_orders),
        'last_submitted_at': state.get('last_submitted_at'),
        'last_ack_at': state.get('last_ack_at'),
        'last_fill_at': state.get('last_fill_at'),
        'bus_metrics': state.get('bus_metrics', {}),
        'recent_events': state.get('events', [])[:25],
    }
