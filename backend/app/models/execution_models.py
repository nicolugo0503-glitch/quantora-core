from typing import Literal, Optional
from pydantic import BaseModel, Field


class ExecutionEnvelope(BaseModel):
    symbol: str = Field(..., min_length=1)
    side: Literal['BUY', 'SELL']
    qty: float = Field(..., gt=0)
    order_type: Literal['MARKET', 'LIMIT'] = 'MARKET'
    price: Optional[float] = Field(default=None, gt=0)
    strategy_id: str = Field(..., min_length=1)
    allocation_id: str = Field(..., min_length=1)
    risk_tag: str = Field(default='STANDARD', min_length=1)
    decision_id: str = Field(..., min_length=1)
    venue_hint: Optional[str] = None
    notional_estimate: Optional[float] = Field(default=None, gt=0)
    portfolio_value_snapshot: Optional[float] = Field(default=None, gt=0)


class ExecutionModeUpdate(BaseModel):
    mode: Literal['paper', 'live']
    safe_mode: bool = True
    broker: Literal['paper', 'binance', 'ibkr'] = 'paper'


class BrokerActivationRequest(BaseModel):
    broker: Literal['paper', 'binance', 'ibkr']
