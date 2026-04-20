from __future__ import annotations

from typing import Any, Dict

from .base_broker import BaseBroker


class IBKRBroker(BaseBroker):
    broker_name = 'ibkr'
    supports_live = True

    def place_order(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'broker': self.broker_name,
            'order_id': 'ibkr_stub',
            'status': 'staged',
            'symbol': str(envelope['symbol']).upper(),
            'side': str(envelope['side']).upper(),
            'qty': float(envelope['qty']),
            'filled_qty': 0.0,
            'fill_price': float(envelope.get('price') or 0.0),
            'executed_at': None,
            'raw': {
                'status': 'stubbed_for_next_mission',
                'note': 'IBKR transport intentionally staged behind QNT50002+ governance gates.'
            },
        }

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return {'broker': self.broker_name, 'order_id': order_id, 'status': 'staged'}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {'broker': self.broker_name, 'order_id': order_id, 'status': 'staged'}
