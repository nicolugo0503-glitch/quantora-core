
import math
from datetime import datetime, timezone
import uuid


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def default_research_memory_state():
    return {
        "notes": [],
        "regime_history": [],
        "telemetry": {
            "notes_ingested": 0,
            "snapshots_built": 0,
            "allocator_evaluations": 0,
            "last_snapshot_at": None,
            "last_regime": "unknown",
        },
    }


def research_memory_state_view(state):
    state = state or {}
    state.setdefault("notes", [])
    state.setdefault("regime_history", [])
    telemetry = state.setdefault("telemetry", {})
    telemetry.setdefault("notes_ingested", 0)
    telemetry.setdefault("snapshots_built", 0)
    telemetry.setdefault("allocator_evaluations", 0)
    telemetry.setdefault("last_snapshot_at", None)
    telemetry.setdefault("last_regime", "unknown")
    return state


def ingest_research_note(state, *, note_type, title, content, market='equities', symbol=None, regime_tag=None, confidence=0.6, horizon='swing', source='manual'):
    state = research_memory_state_view(state)
    note = {
        "note_id": f"rm_{uuid.uuid4().hex[:10]}",
        "created_at": now_iso(),
        "note_type": note_type or 'observation',
        "title": title,
        "content": content,
        "market": (market or 'equities').lower(),
        "symbol": (symbol or '').upper() or None,
        "regime_tag": (regime_tag or '').lower() or None,
        "confidence": max(0.0, min(1.0, float(confidence or 0.0))),
        "horizon": horizon or 'swing',
        "source": source or 'manual',
    }
    state['notes'].insert(0, note)
    state['notes'] = state['notes'][:250]
    state['telemetry']['notes_ingested'] += 1
    return {"status": "ok", "note": note, "summary": research_memory_summary(state)}


def _recent_notes(state, market, symbol=None, limit=20):
    market = (market or 'equities').lower()
    symbol = (symbol or '').upper() or None
    out = []
    for note in state.get('notes', []):
        if note.get('market') != market:
            continue
        if symbol and note.get('symbol') not in (None, symbol):
            continue
        out.append(note)
        if len(out) >= limit:
            break
    return out


def _classify_regime(volatility_bps, breadth, liquidity_score, trend_score, macro_score, notes):
    confidence_boost = sum(float(n.get('confidence', 0.0)) for n in notes[:8]) / max(len(notes[:8]), 1)
    risk_off = volatility_bps >= 220 or liquidity_score < 0.42 or macro_score < 0.35
    breakout = trend_score > 0.68 and breadth > 0.58 and volatility_bps < 180
    mean_revert = volatility_bps >= 150 and 0.35 <= trend_score <= 0.58 and liquidity_score >= 0.45
    if risk_off:
        label = 'risk_off'
    elif breakout:
        label = 'trend_expansion'
    elif mean_revert:
        label = 'mean_reversion'
    else:
        label = 'balanced'
    base_conf = 0.45 + max(0.0, min(0.35, confidence_boost * 0.25))
    feature_conf = min(0.2, abs(trend_score - 0.5) * 0.2 + abs(breadth - 0.5) * 0.15 + max(0, (volatility_bps - 120) / 1000))
    return label, round(min(0.97, base_conf + feature_conf), 4)


def build_regime_snapshot(state, *, market='equities', symbol=None, volatility_bps=120.0, breadth=0.5, liquidity_score=0.7, trend_score=0.5, macro_score=0.5, operator_state=None, performance_state=None, portfolio_risk=None):
    state = research_memory_state_view(state)
    notes = _recent_notes(state, market, symbol)
    regime_label, regime_confidence = _classify_regime(float(volatility_bps), float(breadth), float(liquidity_score), float(trend_score), float(macro_score), notes)
    perf_mem = performance_state or {}
    edge_memory = perf_mem.get('strategy_memory', {}) if isinstance(perf_mem, dict) else {}
    strategy_bias = []
    for sid, item in list(edge_memory.items())[:20]:
        edge_score = float(item.get('edge_score', 50.0))
        action = 'favor' if edge_score >= 60 and regime_label in ('trend_expansion', 'balanced') else 'deemphasize' if edge_score < 45 or regime_label == 'risk_off' else 'observe'
        strategy_bias.append({
            'strategy_id': sid,
            'strategy_name': item.get('strategy_name', sid),
            'edge_score': round(edge_score, 2),
            'action': action,
        })
    risk = portfolio_risk or {}
    limits = risk.get('limits', {}) if isinstance(risk, dict) else {}
    snapshot = {
        'generated_at': now_iso(),
        'market': (market or 'equities').lower(),
        'symbol': (symbol or '').upper() or None,
        'regime_label': regime_label,
        'regime_confidence': regime_confidence,
        'inputs': {
            'volatility_bps': round(float(volatility_bps), 2),
            'breadth': round(float(breadth), 4),
            'liquidity_score': round(float(liquidity_score), 4),
            'trend_score': round(float(trend_score), 4),
            'macro_score': round(float(macro_score), 4),
        },
        'memory_context': {
            'notes_considered': len(notes),
            'top_titles': [n.get('title') for n in notes[:5]],
            'regime_tags': sorted({n.get('regime_tag') for n in notes if n.get('regime_tag')})[:6],
        },
        'strategy_bias': strategy_bias[:8],
        'risk_overlay': {
            'gross_limit_usd': float(limits.get('gross_limit_usd', 0.0) or 0.0),
            'net_limit_usd': float(limits.get('net_limit_usd', 0.0) or 0.0),
        },
    }
    state['regime_history'].insert(0, snapshot)
    state['regime_history'] = state['regime_history'][:150]
    state['telemetry']['snapshots_built'] += 1
    state['telemetry']['last_snapshot_at'] = snapshot['generated_at']
    state['telemetry']['last_regime'] = regime_label
    return snapshot


def evaluate_regime_allocator(state, *, market='equities', symbol=None, volatility_bps=120.0, breadth=0.5, liquidity_score=0.7, trend_score=0.5, macro_score=0.5, operator_state=None, performance_state=None, allocator_state=None, portfolio_risk=None):
    state = research_memory_state_view(state)
    snapshot = build_regime_snapshot(
        state, market=market, symbol=symbol, volatility_bps=volatility_bps, breadth=breadth,
        liquidity_score=liquidity_score, trend_score=trend_score, macro_score=macro_score,
        operator_state=operator_state, performance_state=performance_state, portfolio_risk=portfolio_risk
    )
    strategies = ((operator_state or {}).get('strategies') or {}).get('strategies', [])
    metrics = ((operator_state or {}).get('strategy_engine') or {}).get('metrics', {})
    adjustments = []
    multiplier = {
        'risk_off': 0.72,
        'trend_expansion': 1.18,
        'mean_reversion': 1.05,
        'balanced': 1.0,
    }.get(snapshot['regime_label'], 1.0)
    for strategy in strategies:
        sid = strategy.get('strategy_id')
        metric = metrics.get(sid, {})
        capital_limit = float(strategy.get('capital_limit', 0.0) or 0.0)
        realized = float(metric.get('realized_pnl', 0.0) or 0.0)
        confidence = float(strategy.get('ai_confidence', 0.5) or 0.5)
        perf_bias = 1.05 if realized > 0 else 0.92 if realized < 0 else 1.0
        conf_bias = 0.9 + (confidence * 0.25)
        proposed = round(capital_limit * multiplier * perf_bias * conf_bias, 2)
        delta = round(proposed - capital_limit, 2)
        action = 'hold'
        if delta >= max(250.0, capital_limit * 0.08):
            action = 'increase'
        elif delta <= -max(250.0, capital_limit * 0.08):
            action = 'decrease'
        adjustments.append({
            'strategy_id': sid,
            'strategy_name': strategy.get('name', sid),
            'current_capital_limit': capital_limit,
            'proposed_capital_limit': max(0.0, proposed),
            'delta': delta,
            'action': action,
            'driver': snapshot['regime_label'],
        })
    state['telemetry']['allocator_evaluations'] += 1
    return {
        'status': 'ok',
        'snapshot': snapshot,
        'adjustments': adjustments,
        'summary': research_memory_summary(state),
    }


def research_memory_summary(state):
    state = research_memory_state_view(state)
    notes = state.get('notes', [])
    last_regime = state.get('telemetry', {}).get('last_regime', 'unknown')
    return {
        'notes': len(notes),
        'regime_history': len(state.get('regime_history', [])),
        'last_regime': last_regime,
        'notes_by_market': {m: sum(1 for n in notes if n.get('market') == m) for m in sorted({n.get('market') for n in notes})},
        'telemetry': state.get('telemetry', {}),
    }
