from __future__ import annotations

from .base_broker import BaseBroker
from .binance_broker import BinanceBroker
from .ibkr_broker import IBKRBroker
from .paper_broker import PaperBroker


AVAILABLE_BROKERS = {
    'paper': PaperBroker,
    'binance': BinanceBroker,
    'ibkr': IBKRBroker,
}


def get_broker(name: str) -> BaseBroker:
    broker_cls = AVAILABLE_BROKERS.get((name or 'paper').strip().lower())
    if broker_cls is None:
        raise ValueError(f'unsupported broker: {name}')
    return broker_cls()
