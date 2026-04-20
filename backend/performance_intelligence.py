
import math
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def default_performance_intelligence_state():
    return {
        "enabled": True,
        "last_snapshot_at": None,
        "last_ingest_at": None,
        "last_rebalance_at": None,
        "strategy_memory": {},
        "attribution_events": [],
        "meta_allocator": {
            "promotion_threshold": 72.0,
            "decay_threshold": 44.0,
            "capital_boost_ratio": 0.18,
            "capital_decay_ratio": 0.12,
            "max_promoted": 3,
            "min_observations": 3,
        },
        "telemetry": {
            "events_ingested": 0,
            "snapshots_built": 0,
            "rebalance_runs": 0,
            "capital_applications": 0,
        },
    }


def performance_state_view(state):
    state = state or default_performance_intelligence_state()
    defaults = default_performance_intelligence_state()
    for k, v in defaults.items():
        if isinstance(v, dict):
            state.setdefault(k, v.copy())
        elif isinstance(v, list):
            state.setdefault(k, list(v))
        else:
            state.setdefault(k, v)
    for k, v in defaults['meta_allocator'].items():
        state['meta_allocator'].setdefault(k, v)
    for k, v in defaults['telemetry'].items():
        state['telemetry'].setdefault(k, v)
    state.setdefault('strategy_memory', {})
    state.setdefault('attribution_events', [])
    return state


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def ingest_attribution_event(state, *, strategy_id, strategy_name=None, pnl=0.0, capital_used=0.0, trades=1, win_rate=None, confidence=None, source='manual'):
    state = performance_state_view(state)
    strategy_id = strategy_id or 'unknown'
    event = {
        'event_id': f'perf_{len(state["attribution_events"]) + 1:06d}',
        'recorded_at': now_iso(),
        'strategy_id': strategy_id,
        'strategy_name': strategy_name or strategy_id,
        'pnl': round(_safe_float(pnl), 2),
        'capital_used': round(max(0.0, _safe_float(capital_used)), 2),
        'trades': max(1, _safe_int(trades, 1)),
        'win_rate': None if win_rate is None else round(max(0.0, min(1.0, _safe_float(win_rate))), 4),
        'confidence': None if confidence is None else round(max(0.0, min(1.0, _safe_float(confidence))), 4),
        'source': source,
    }
    state['attribution_events'].append(event)
    state['attribution_events'] = state['attribution_events'][-250:]
    memory = state['strategy_memory'].setdefault(strategy_id, {
        'strategy_id': strategy_id,
        'strategy_name': strategy_name or strategy_id,
        'observations': 0,
        'total_pnl': 0.0,
        'total_capital_used': 0.0,
        'total_trades': 0,
        'last_pnl': 0.0,
        'last_win_rate': None,
        'last_confidence': None,
        'recent_pnls': [],
        'edge_score': 50.0,
        'decay_score': 0.0,
        'allocation_multiplier': 1.0,
    })
    memory['strategy_name'] = strategy_name or memory.get('strategy_name') or strategy_id
    memory['observations'] = int(memory.get('observations', 0)) + 1
    memory['total_pnl'] = round(_safe_float(memory.get('total_pnl')) + event['pnl'], 2)
    memory['total_capital_used'] = round(_safe_float(memory.get('total_capital_used')) + event['capital_used'], 2)
    memory['total_trades'] = int(memory.get('total_trades', 0)) + event['trades']
    memory['last_pnl'] = event['pnl']
    memory['last_win_rate'] = event['win_rate']
    memory['last_confidence'] = event['confidence']
    memory.setdefault('recent_pnls', []).append(event['pnl'])
    memory['recent_pnls'] = memory['recent_pnls'][-12:]
    state['last_ingest_at'] = event['recorded_at']
    state['telemetry']['events_ingested'] = int(state['telemetry'].get('events_ingested', 0)) + 1
    return event


def _memory_metrics(memory):
    observations = max(1, int(memory.get('observations', 0)))
    total_pnl = _safe_float(memory.get('total_pnl'))
    total_capital = max(_safe_float(memory.get('total_capital_used')), 1.0)
    total_trades = max(1, int(memory.get('total_trades', 0)))
    avg_pnl = total_pnl / observations
    pnl_efficiency = total_pnl / total_capital
    expectancy = total_pnl / total_trades
    recent = list(memory.get('recent_pnls', []))[-6:]
    persistence = 0.5
    if recent:
        positive = len([x for x in recent if x > 0]) / len(recent)
        persistence = positive
    stability = 1.0
    if len(recent) >= 2:
        mean = sum(recent) / len(recent)
        var = sum((x - mean) ** 2 for x in recent) / len(recent)
        std = math.sqrt(var)
        stability = max(0.0, min(1.0, 1.0 - (std / max(abs(mean), 500.0))))
    return {
        'avg_pnl': round(avg_pnl, 2),
        'pnl_efficiency': round(pnl_efficiency, 6),
        'expectancy': round(expectancy, 2),
        'persistence': round(persistence, 4),
        'stability': round(stability, 4),
    }


def build_performance_snapshot(state, operator_state=None, allocator_state=None):
    state = performance_state_view(state)
    rows = []
    metrics_map = ((operator_state or {}).get('strategy_engine') or {}).get('metrics') or {}
    strategies = ((operator_state or {}).get('strategies') or {}).get('strategies') or []
    strategy_names = {s.get('strategy_id'): s for s in strategies}
    all_ids = set(state.get('strategy_memory', {}).keys()) | set(metrics_map.keys()) | {s.get('strategy_id') for s in strategies if s.get('strategy_id')}
    for strategy_id in sorted(all_ids):
        memory = state['strategy_memory'].setdefault(strategy_id, {
            'strategy_id': strategy_id,
            'strategy_name': (strategy_names.get(strategy_id) or {}).get('name') or strategy_id,
            'observations': 0,
            'total_pnl': 0.0,
            'total_capital_used': 0.0,
            'total_trades': 0,
            'recent_pnls': [],
            'edge_score': 50.0,
            'decay_score': 0.0,
            'allocation_multiplier': 1.0,
        })
        metric = metrics_map.get(strategy_id, {})
        realized = _safe_float(metric.get('realized_pnl'))
        unrealized = _safe_float(metric.get('unrealized_pnl'))
        live_win = _safe_float(metric.get('win_rate'))
        if live_win > 1:
            live_win = live_win / 100.0
        live_conf = _safe_float((strategy_names.get(strategy_id) or {}).get('ai_confidence') or metric.get('confidence'), 0.55)
        capital_in_use = _safe_float(metric.get('capital_in_use') or (strategy_names.get(strategy_id) or {}).get('capital_limit'))
        meta = _memory_metrics(memory)
        total_pnl = realized + unrealized + _safe_float(memory.get('total_pnl'))
        efficiency_component = max(0.0, min(1.0, (meta['pnl_efficiency'] + 0.12) / 0.24))
        persistence_component = meta['persistence']
        stability_component = meta['stability']
        confidence_component = max(0.0, min(1.0, live_conf))
        win_component = max(0.0, min(1.0, live_win if live_win else 0.5))
        edge_score = round(100.0 * ((efficiency_component * 0.30) + (persistence_component * 0.24) + (stability_component * 0.16) + (confidence_component * 0.15) + (win_component * 0.15)), 2)
        decay_score = round(100.0 - edge_score if total_pnl < 0 else max(0.0, 55.0 - edge_score), 2)
        row = {
            'strategy_id': strategy_id,
            'name': memory.get('strategy_name') or (strategy_names.get(strategy_id) or {}).get('name') or strategy_id,
            'observations': int(memory.get('observations', 0)),
            'realized_pnl': round(realized, 2),
            'unrealized_pnl': round(unrealized, 2),
            'memory_pnl': round(_safe_float(memory.get('total_pnl')), 2),
            'capital_in_use': round(capital_in_use, 2),
            'avg_pnl': meta['avg_pnl'],
            'expectancy': meta['expectancy'],
            'persistence': round(meta['persistence'] * 100.0, 2),
            'stability': round(meta['stability'] * 100.0, 2),
            'edge_score': edge_score,
            'decay_score': decay_score,
            'live_confidence': round(live_conf * 100.0, 2),
            'live_win_rate': round(win_component * 100.0, 2),
            'allocator_budget': (((allocator_state or {}).get('strategy_budgets') or {}).get(strategy_id) or {}).get('target_capital_usd'),
            'current_capital_limit': round(_safe_float((strategy_names.get(strategy_id) or {}).get('capital_limit')), 2),
        }
        memory['edge_score'] = edge_score
        memory['decay_score'] = decay_score
        rows.append(row)
    rows.sort(key=lambda r: (-r['edge_score'], r['name'] or ''))
    snapshot = {
        'generated_at': now_iso(),
        'strategies': rows,
        'summary': performance_summary(state, rows),
    }
    state['last_snapshot_at'] = snapshot['generated_at']
    state['telemetry']['snapshots_built'] = int(state['telemetry'].get('snapshots_built', 0)) + 1
    return snapshot


def evaluate_meta_allocator(state, operator_state=None, allocator_state=None):
    state = performance_state_view(state)
    snapshot = build_performance_snapshot(state, operator_state=operator_state, allocator_state=allocator_state)
    policy = state['meta_allocator']
    promote_threshold = _safe_float(policy.get('promotion_threshold'), 72.0)
    decay_threshold = _safe_float(policy.get('decay_threshold'), 44.0)
    boost_ratio = _safe_float(policy.get('capital_boost_ratio'), 0.18)
    decay_ratio = _safe_float(policy.get('capital_decay_ratio'), 0.12)
    max_promoted = max(1, _safe_int(policy.get('max_promoted'), 3))
    min_obs = max(1, _safe_int(policy.get('min_observations'), 3))
    promoted = 0
    proposals = []
    for row in snapshot['strategies']:
        action = 'hold'
        multiplier = 1.0
        rationale = 'insufficient edge persistence'
        if row['observations'] >= min_obs and row['edge_score'] >= promote_threshold and promoted < max_promoted:
            action = 'boost'
            multiplier = round(1.0 + boost_ratio, 4)
            rationale = 'persistent edge and stable attribution'
            promoted += 1
        elif row['observations'] >= min_obs and row['edge_score'] <= decay_threshold:
            action = 'decay'
            multiplier = round(max(0.5, 1.0 - decay_ratio), 4)
            rationale = 'weak edge persistence or negative expectancy'
        current_capital = _safe_float(row.get('allocator_budget') or row.get('current_capital_limit'), 0.0)
        target_capital = round(current_capital * multiplier, 2) if current_capital > 0 else 0.0
        proposals.append({
            'strategy_id': row['strategy_id'],
            'name': row['name'],
            'edge_score': row['edge_score'],
            'decay_score': row['decay_score'],
            'action': action,
            'multiplier': multiplier,
            'current_capital_usd': round(current_capital, 2),
            'target_capital_usd': target_capital,
            'delta_usd': round(target_capital - current_capital, 2),
            'rationale': rationale,
        })
        state['strategy_memory'][row['strategy_id']]['allocation_multiplier'] = multiplier
    state['last_rebalance_at'] = now_iso()
    state['telemetry']['rebalance_runs'] = int(state['telemetry'].get('rebalance_runs', 0)) + 1
    return {
        'status': 'ok',
        'generated_at': state['last_rebalance_at'],
        'proposals': proposals,
        'summary': performance_summary(state, snapshot['strategies'], proposals),
    }


def apply_meta_allocation(state, operator_state=None, allocator_state=None):
    state = performance_state_view(state)
    operator_state = operator_state or {}
    result = evaluate_meta_allocator(state, operator_state=operator_state, allocator_state=allocator_state)
    proposals = {p['strategy_id']: p for p in result['proposals']}
    changed = []
    for strategy in ((operator_state.get('strategies') or {}).get('strategies') or []):
        proposal = proposals.get(strategy.get('strategy_id'))
        if not proposal:
            continue
        current_limit = _safe_float(strategy.get('capital_limit'), 0.0)
        if current_limit <= 0:
            continue
        new_limit = max(100.0, round(current_limit * proposal['multiplier'], 2))
        if abs(new_limit - current_limit) >= 1.0:
            strategy['capital_limit'] = new_limit
            changed.append({
                'strategy_id': strategy.get('strategy_id'),
                'name': strategy.get('name'),
                'from_capital_usd': round(current_limit, 2),
                'to_capital_usd': new_limit,
                'action': proposal['action'],
            })
    state['telemetry']['capital_applications'] = int(state['telemetry'].get('capital_applications', 0)) + 1
    return {
        'status': 'ok',
        'applied_at': now_iso(),
        'changes': changed,
        'summary': performance_summary(state),
    }


def performance_summary(state, rows=None, proposals=None):
    state = performance_state_view(state)
    rows = rows or []
    proposals = proposals or []
    return {
        'tracked_strategies': len(rows) if rows else len(state.get('strategy_memory', {})),
        'promotions': len([p for p in proposals if p.get('action') == 'boost']),
        'decays': len([p for p in proposals if p.get('action') == 'decay']),
        'holds': len([p for p in proposals if p.get('action') == 'hold']),
        'events_ingested': int(state.get('telemetry', {}).get('events_ingested', 0)),
        'avg_edge_score': round(sum(r.get('edge_score', 0.0) for r in rows) / max(len(rows), 1), 2) if rows else 0.0,
        'last_snapshot_at': state.get('last_snapshot_at'),
        'last_rebalance_at': state.get('last_rebalance_at'),
    }
