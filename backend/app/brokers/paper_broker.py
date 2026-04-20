from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from .base_broker import BaseBroker


class PaperBroker(BaseBroker):
    broker_name = 'paper'
    supports_live = False

    def place_order(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        price = float(envelope.get('price') or 100.0)
        qty = float(envelope['qty'])
        side = str(envelope['side']).upper()
        slip = 0.0005
        fill_price = round(price * (1.0 + slip if side == 'BUY' else 1.0 - slip), 6)
        now = int(time.time())
        return {
            'broker': self.broker_name,
            'order_id': f'paper_{uuid.uuid4().hex[:18]}',
            'status': 'filled',
            'symbol': str(envelope['symbol']).upper(),
            'side': side,
            'qty': qty,
            'filled_qty': qty,
            'fill_price': fill_price,
            'executed_at': now,
            'raw': {'simulation': True},
        }

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return {'broker': self.broker_name, 'order_id': order_id, 'status': 'filled'}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {'broker': self.broker_name, 'order_id': order_id, 'status': 'not_cancellable'}
