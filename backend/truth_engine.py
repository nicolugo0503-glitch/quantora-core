
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ''):
            return default
        return float(value)
    except Exception:
        return default


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'


def normalize_local_positions(local_positions: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    rows = []
    for pos in local_positions or []:
        qty = _f(pos.get('qty', pos.get('net_qty', 0)))
        if abs(qty) <= 0:
            continue
        rows.append({
            'symbol': (pos.get('symbol') or 'UNK').upper(),
            'qty': round(qty, 6),
            'market_value': round(abs(_f(pos.get('market_value'))), 2),
            'current_price': round(_f(pos.get('current_price', pos.get('last_price'))), 4),
            'avg_entry': round(_f(pos.get('avg_entry', pos.get('avg_fill'))), 4),
            'source': 'local',
        })
    rows.sort(key=lambda x: x['symbol'])
    return rows


def normalize_broker_positions(broker_positions: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    rows = []
    for pos in broker_positions or []:
        qty = _f(pos.get('qty', pos.get('net_qty', 0)))
        if abs(qty) <= 0:
            continue
        rows.append({
            'symbol': (pos.get('symbol') or 'UNK').upper(),
            'qty': round(qty, 6),
            'market_value': round(abs(_f(pos.get('market_value'))), 2),
            'current_price': round(_f(pos.get('current_price', pos.get('last_price'))), 4),
            'avg_entry': round(_f(pos.get('avg_entry_price', pos.get('avg_entry', pos.get('avg_fill')))), 4),
            'source': 'broker',
        })
    rows.sort(key=lambda x: x['symbol'])
    return rows


def build_truth_snapshot(local_positions: List[Dict[str, Any]] | None, broker_positions: List[Dict[str, Any]] | None, account: Dict[str, Any] | None = None) -> Dict[str, Any]:
    local_rows = normalize_local_positions(local_positions)
    broker_rows = normalize_broker_positions(broker_positions)
    account = account or {}
    local_map = {row['symbol']: row for row in local_rows}
    broker_map = {row['symbol']: row for row in broker_rows}
    symbols = sorted(set(local_map) | set(broker_map))

    mismatches = []
    trusted_positions = []
    for symbol in symbols:
        l = local_map.get(symbol)
        b = broker_map.get(symbol)
        trusted = b or l
        if trusted:
            trusted_positions.append({**trusted, 'truth_source': 'broker' if b else 'local'})
        if not l or not b:
            mismatches.append({
                'symbol': symbol,
                'severity': 'warn',
                'reason': 'missing-on-one-side',
                'local_qty': l['qty'] if l else 0.0,
                'broker_qty': b['qty'] if b else 0.0,
            })
            continue
        if round(l['qty'], 6) != round(b['qty'], 6):
            mismatches.append({
                'symbol': symbol,
                'severity': 'critical',
                'reason': 'qty-mismatch',
                'local_qty': l['qty'],
                'broker_qty': b['qty'],
            })
        elif round(l.get('market_value', 0.0), 2) != round(b.get('market_value', 0.0), 2):
            mismatches.append({
                'symbol': symbol,
                'severity': 'warn',
                'reason': 'market-value-mismatch',
                'local_market_value': l.get('market_value', 0.0),
                'broker_market_value': b.get('market_value', 0.0),
            })

    unrealized = round(sum(_f(p.get('market_value')) - (_f(p.get('avg_entry')) * _f(p.get('qty'))) for p in trusted_positions), 2)
    equity = round(_f(account.get('equity')), 2)
    cash = round(_f(account.get('cash')), 2)
    buying_power = round(_f(account.get('buying_power', account.get('regt_buying_power'))), 2)

    return {
        'generated_at': _now(),
        'truth_source': 'broker' if broker_rows else 'local',
        'positions': trusted_positions,
        'counts': {
            'local_positions': len(local_rows),
            'broker_positions': len(broker_rows),
            'truth_positions': len(trusted_positions),
            'mismatches': len(mismatches),
        },
        'account': {
            'equity': equity,
            'cash': cash,
            'buying_power': buying_power,
        },
        'pnl': {
            'unrealized': unrealized,
            'equity': equity,
        },
        'mismatches': mismatches,
    }
