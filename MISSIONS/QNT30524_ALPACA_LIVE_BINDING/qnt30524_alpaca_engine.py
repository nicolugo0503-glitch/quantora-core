# QNT30524 — Alpaca Live Broker Binding (audit-fixed)

import os
import requests
from datetime import datetime, timezone


def _ts():
    return datetime.now(timezone.utc).isoformat()


class AlpacaBrokerAdapter:
    def __init__(self, api_key=None, api_secret=None, base_url=None):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.api_secret = api_secret or os.getenv("ALPACA_API_SECRET", "")
        self.base_url = base_url or os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    def _headers(self):
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }

    def _request(self, method, path, payload=None):
        url = f"{self.base_url}{path}"
        r = requests.request(method, url, json=payload, headers=self._headers(), timeout=20)
        try:
            return r.json()
        except Exception:
            return {"status_code": r.status_code, "text": r.text}

    def submit_order(self, order):
        payload = {
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "type": order.get("type", "market"),
            "time_in_force": order.get("time_in_force", "gtc"),
        }

        if order.get("qty") is not None:
            payload["qty"] = order.get("qty")
        elif order.get("notional") is not None:
            payload["notional"] = order.get("notional")
        else:
            payload["qty"] = 1

        if order.get("limit_price") is not None:
            payload["limit_price"] = order.get("limit_price")
        if order.get("stop_price") is not None:
            payload["stop_price"] = order.get("stop_price")

        return self._request("POST", "/v2/orders", payload)

    def get_all_positions(self):
        data = self._request("GET", "/v2/positions")
        if isinstance(data, list):
            rows = []
            for row in data:
                rows.append({
                    "symbol": row.get("symbol"),
                    "qty": float(row.get("qty", 0.0) or 0.0),
                    "market_value": float(row.get("market_value", 0.0) or 0.0),
                    "unrealized_pnl": float(row.get("unrealized_pl", 0.0) or 0.0),
                    "realized_pnl": float(row.get("realized_pl", 0.0) or 0.0),
                })
            return rows
        return []

    def get_account(self):
        data = self._request("GET", "/v2/account")
        if isinstance(data, dict):
            return {
                "equity": float(data.get("equity", 0.0) or 0.0),
                "cash": float(data.get("cash", 0.0) or 0.0),
                "buying_power": float(data.get("buying_power", 0.0) or 0.0),
                "status": data.get("status", ""),
            }
        return {}

    def get_open_orders(self):
        data = self._request("GET", "/v2/orders?status=open")
        return data if isinstance(data, list) else []

    def get_recent_fills(self):
        # Alpaca fills typically come through activities; this is a minimal normalized adapter.
        data = self._request("GET", "/v2/account/activities/FILL")
        return data if isinstance(data, list) else []


class QNT30524LiveExecution:
    def __init__(self, broker: AlpacaBrokerAdapter):
        self.broker = broker
        self.history = []

    def execute_live(self, orders):
        results = []
        for o in orders:
            results.append(self.broker.submit_order(o))

        record = {
            "timestamp": _ts(),
            "orders": results,
            "submitted_count": len(results),
        }
        self.history.append(record)
        self.history = self.history[-100:]
        return record

    def get_history(self):
        return self.history[-100:]
