from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict

from .base_broker import BaseBroker


class BinanceBroker(BaseBroker):
    broker_name = 'binance'
    supports_live = True
    base_url = 'https://api.binance.com'

    def _credentials(self) -> tuple[str, str]:
        api_key = os.getenv('BINANCE_API_KEY', '').strip()
        api_secret = os.getenv('BINANCE_SECRET', '').strip()
        if not api_key or not api_secret:
            raise RuntimeError('missing BINANCE_API_KEY or BINANCE_SECRET')
        return api_key, api_secret

    def _signed_params(self, envelope: Dict[str, Any]) -> tuple[str, Dict[str, str]]:
        _, secret = self._credentials()
        params = {
            'symbol': str(envelope['symbol']).upper(),
            'side': str(envelope['side']).upper(),
            'type': str(envelope.get('order_type') or 'MARKET').upper(),
            'quantity': f"{float(envelope['qty']):.8f}".rstrip('0').rstrip('.'),
            'timestamp': str(int(time.time() * 1000)),
            'newOrderRespType': 'FULL',
        }
        if params['type'] == 'LIMIT':
            price = envelope.get('price')
            if price is None:
                raise RuntimeError('LIMIT order requires price')
            params['price'] = f"{float(price):.8f}".rstrip('0').rstrip('.')
            params['timeInForce'] = 'GTC'
        query = urllib.parse.urlencode(params)
        signature = hmac.new(secret.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature
        return urllib.parse.urlencode(params), {'X-MBX-APIKEY': self._credentials()[0]}

    def place_order(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        query, headers = self._signed_params(envelope)
        url = f'{self.base_url}/api/v3/order?{query}'
        req = urllib.request.Request(url, method='POST', headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = resp.read().decode('utf-8')
        import json
        data = json.loads(payload)
        fills = data.get('fills') or []
        avg_price = 0.0
        if fills:
            total_qty = sum(float(f.get('qty', 0.0)) for f in fills) or float(envelope['qty'])
            total_notional = sum(float(f.get('qty', 0.0)) * float(f.get('price', 0.0)) for f in fills)
            avg_price = round(total_notional / total_qty, 8) if total_qty else 0.0
        return {
            'broker': self.broker_name,
            'order_id': str(data.get('orderId') or data.get('clientOrderId') or ''),
            'status': str(data.get('status') or 'submitted').lower(),
            'symbol': data.get('symbol') or str(envelope['symbol']).upper(),
            'side': data.get('side') or str(envelope['side']).upper(),
            'qty': float(data.get('origQty') or envelope['qty']),
            'filled_qty': float(data.get('executedQty') or 0.0),
            'fill_price': avg_price or float(envelope.get('price') or 0.0),
            'executed_at': int(time.time()),
            'raw': data,
        }

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return {'broker': self.broker_name, 'order_id': order_id, 'status': 'external_lookup_required'}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {'broker': self.broker_name, 'order_id': order_id, 'status': 'external_cancel_required'}
