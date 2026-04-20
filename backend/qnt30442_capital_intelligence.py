from __future__ import annotations

from typing import Dict, Iterable, List, Tuple
from math import sqrt


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _bounded(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _risk_level(score: float, loss_ratio: float, utilization: float) -> str:
    if loss_ratio >= 0.12 or score < 45 or utilization > 1.15:
        return 'high'
    if loss_ratio >= 0.05 or score < 70 or utilization > 0.9:
        return 'medium'
    return 'low'


def aggregate_strategy_metrics(strategies: Iterable[Dict], allocations: Iterable[Dict], positions: Iterable[Dict], fills: Iterable[Dict]) -> List[Dict]:
    registry = {}
    for item in strategies or []:
        key = (item.get('strategy_key') or '').strip()
        if not key:
            continue
        registry[key] = {
            'strategy_key': key,
            'display_name': item.get('display_name') or key,
            'market': item.get('market') or 'multi-asset',
            'status': item.get('status') or 'active',
            'allocated_capital': 0.0,
            'reserve_capital': 0.0,
            'gross_exposure': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'net_pnl': 0.0,
            'fill_count': 0,
            'traded_notional': 0.0,
            'position_count': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'capital_efficiency': 0.0,
            'utilization': 0.0,
            'loss_ratio': 0.0,
            'consistency': 0.0,
            'score': 0.0,
            'rank': None,
            'risk_level': 'unknown',
            'score_breakdown': {},
        }

    def ensure_strategy(key: str) -> Dict:
        key = (key or '').strip()
        if not key:
            key = 'unassigned'
        if key not in registry:
            registry[key] = {
                'strategy_key': key,
                'display_name': key.replace('_', ' ').title(),
                'market': 'multi-asset',
                'status': 'active',
                'allocated_capital': 0.0,
                'reserve_capital': 0.0,
                'gross_exposure': 0.0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'net_pnl': 0.0,
                'fill_count': 0,
                'traded_notional': 0.0,
                'position_count': 0,
                'winning_positions': 0,
                'losing_positions': 0,
                'capital_efficiency': 0.0,
                'utilization': 0.0,
                'loss_ratio': 0.0,
                'consistency': 0.0,
                'score': 0.0,
                'rank': None,
                'risk_level': 'unknown',
                'score_breakdown': {},
            }
        return registry[key]

    for item in allocations or []:
        if (item.get('status') or 'active') not in {'active', 'approved'}:
            continue
        row = ensure_strategy(item.get('strategy_key'))
        row['allocated_capital'] += _as_float(item.get('allocated_capital'))
        row['reserve_capital'] += _as_float(item.get('reserve_capital'))

    for item in positions or []:
        row = ensure_strategy(item.get('strategy_key'))
        row['position_count'] += 1
        realized = _as_float(item.get('realized_pnl'))
        unrealized = _as_float(item.get('unrealized_pnl'))
        row['realized_pnl'] += realized
        row['unrealized_pnl'] += unrealized
        row['gross_exposure'] += abs(_as_float(item.get('market_value')) or (_as_float(item.get('qty')) * _as_float(item.get('market_price') or item.get('avg_price'))))
        total_pnl = realized + unrealized
        if total_pnl > 0:
            row['winning_positions'] += 1
        elif total_pnl < 0:
            row['losing_positions'] += 1

    for item in fills or []:
        row = ensure_strategy(item.get('strategy_key'))
        row['fill_count'] += 1
        row['traded_notional'] += abs(_as_float(item.get('fill_value')) or (_as_float(item.get('qty')) * _as_float(item.get('fill_price'))))

    rows = list(registry.values())
    for row in rows:
        row['net_pnl'] = round(row['realized_pnl'] + row['unrealized_pnl'], 4)
        denominator = row['allocated_capital'] or row['gross_exposure'] or 1.0
        row['capital_efficiency'] = round(row['net_pnl'] / denominator, 6)
        row['utilization'] = round(row['gross_exposure'] / (row['allocated_capital'] or row['gross_exposure'] or 1.0), 6)
        row['loss_ratio'] = round(max(0.0, -row['net_pnl']) / denominator, 6)
        outcomes = row['winning_positions'] + row['losing_positions']
        if outcomes:
            row['consistency'] = round(row['winning_positions'] / outcomes, 6)
        elif row['fill_count']:
            row['consistency'] = 0.5
        else:
            row['consistency'] = 0.0

    if not rows:
        return []

    pnl_values = [r['net_pnl'] for r in rows]
    eff_values = [r['capital_efficiency'] for r in rows]
    risk_values = [r['loss_ratio'] for r in rows]
    util_scores = []
    for r in rows:
        util = r['utilization']
        util_scores.append(_bounded(1 - abs(util - 0.72) / 0.72))

    pnl_min, pnl_max = min(pnl_values), max(pnl_values)
    eff_min, eff_max = min(eff_values), max(eff_values)
    risk_min, risk_max = min(risk_values), max(risk_values)

    def normalize(value: float, low: float, high: float, neutral: float = 0.5) -> float:
        if abs(high - low) < 1e-9:
            return neutral
        return _bounded((value - low) / (high - low))

    for idx, row in enumerate(rows):
        pnl_norm = normalize(row['net_pnl'], pnl_min, pnl_max, 0.5)
        eff_norm = normalize(row['capital_efficiency'], eff_min, eff_max, 0.5)
        risk_norm = normalize(row['loss_ratio'], risk_min, risk_max, 0.0)
        util_norm = util_scores[idx]
        consistency_norm = _bounded(row['consistency'])
        score = (
            pnl_norm * 32.0
            + eff_norm * 24.0
            + (1 - risk_norm) * 18.0
            + consistency_norm * 16.0
            + util_norm * 10.0
        )
        row['score'] = round(score, 2)
        row['risk_level'] = _risk_level(row['score'], row['loss_ratio'], row['utilization'])
        row['score_breakdown'] = {
            'pnl': round(pnl_norm * 32.0, 2),
            'efficiency': round(eff_norm * 24.0, 2),
            'risk': round((1 - risk_norm) * 18.0, 2),
            'consistency': round(consistency_norm * 16.0, 2),
            'utilization': round(util_norm * 10.0, 2),
        }

    rows.sort(key=lambda r: (r['score'], r['net_pnl'], r['capital_efficiency']), reverse=True)
    for index, row in enumerate(rows, start=1):
        row['rank'] = index
    return rows


def build_rebalance_recommendations(strategy_rows: List[Dict]) -> List[Dict]:
    active = [r for r in strategy_rows if (r.get('status') or 'active') == 'active']
    if len(active) < 2:
        return []
    total_allocated = sum(_as_float(r.get('allocated_capital')) for r in active)
    if total_allocated <= 0:
        return []

    weighted_scores = []
    for r in active:
        weighted_scores.append(max(0.15, _as_float(r.get('score')) / 100.0) ** 1.35)
    weight_sum = sum(weighted_scores) or 1.0

    enriched = []
    for r, weight in zip(active, weighted_scores):
        target = total_allocated * (weight / weight_sum)
        current = _as_float(r.get('allocated_capital'))
        delta = target - current
        enriched.append({**r, 'target_capital': round(target, 2), 'delta_to_target': round(delta, 2)})

    min_trade = max(500.0, round(total_allocated * 0.05 / max(len(active), 1), 2))
    donors = [r.copy() for r in sorted(enriched, key=lambda x: x['delta_to_target']) if r['delta_to_target'] < -min_trade]
    receivers = [r.copy() for r in sorted(enriched, key=lambda x: x['delta_to_target'], reverse=True) if r['delta_to_target'] > min_trade]

    recommendations: List[Dict] = []
    rec_index = 1
    for receiver in receivers:
        need = receiver['delta_to_target']
        for donor in donors:
            available = abs(donor['delta_to_target'])
            if need <= 0 or available <= 0:
                continue
            amount = round(min(need, available), 2)
            if amount < min_trade:
                continue
            score_gap = max(0.0, _as_float(receiver.get('score')) - _as_float(donor.get('score')))
            confidence = _bounded(0.55 + (score_gap / 120.0) + (_as_float(receiver.get('capital_efficiency')) * 1.2), 0.0, 0.98)
            recommendations.append({
                'recommendation_id': f'ci_rec_{rec_index:03d}',
                'action': 'rebalance',
                'from_strategy_key': donor['strategy_key'],
                'to_strategy_key': receiver['strategy_key'],
                'from_display_name': donor.get('display_name') or donor['strategy_key'],
                'to_display_name': receiver.get('display_name') or receiver['strategy_key'],
                'amount': amount,
                'confidence': round(confidence, 2),
                'manual_approval_required': True,
                'reason': f"Shift capital from {donor.get('display_name') or donor['strategy_key']} to {receiver.get('display_name') or receiver['strategy_key']} based on score gap, efficiency, and target allocation drift.",
                'from_score': donor.get('score'),
                'to_score': receiver.get('score'),
                'from_risk_level': donor.get('risk_level'),
                'to_risk_level': receiver.get('risk_level'),
            })
            donor['delta_to_target'] = round(donor['delta_to_target'] + amount, 2)
            need = round(need - amount, 2)
            rec_index += 1
    return recommendations


def build_capital_intelligence_package(strategies: Iterable[Dict], allocations: Iterable[Dict], positions: Iterable[Dict], fills: Iterable[Dict]) -> Dict:
    rows = aggregate_strategy_metrics(strategies, allocations, positions, fills)
    recommendations = build_rebalance_recommendations(rows)
    total_allocated = round(sum(_as_float(r.get('allocated_capital')) for r in rows), 2)
    total_reserve = round(sum(_as_float(r.get('reserve_capital')) for r in rows), 2)
    total_pnl = round(sum(_as_float(r.get('net_pnl')) for r in rows), 2)
    avg_score = round(sum(_as_float(r.get('score')) for r in rows) / len(rows), 2) if rows else 0.0
    top = rows[0] if rows else None
    return {
        'summary': {
            'module': 'QNT30442',
            'manual_control_mode': True,
            'strategy_count': len(rows),
            'total_allocated_capital': total_allocated,
            'total_reserve_capital': total_reserve,
            'total_net_pnl': total_pnl,
            'average_strategy_score': avg_score,
            'top_strategy': top.get('display_name') if top else None,
            'top_strategy_score': top.get('score') if top else None,
            'recommendation_count': len(recommendations),
        },
        'strategies': rows,
        'recommendations': recommendations,
    }
