from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class AutonomousExecutionConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_execute_paper: Optional[bool] = None
    auto_execute_live: Optional[bool] = None
    require_committee_ticket_for_live: Optional[bool] = None
    max_orders_per_cycle: Optional[int] = Field(default=None, ge=1, le=100)
    max_cycle_notional: Optional[float] = Field(default=None, ge=0)
    minimum_sharpe_ratio: Optional[float] = Field(default=None, ge=-10, le=10)
    maximum_drawdown_pct: Optional[float] = Field(default=None, ge=0, le=1)
    allow_regime_stress: Optional[bool] = None
    default_order_type: Optional[Literal['MARKET', 'LIMIT']] = None
    participation_rate: Optional[float] = Field(default=None, gt=0, le=1)
    price_map: Optional[Dict[str, float]] = None


class AutonomousReleaseIngestRequest(BaseModel):
    queue_index: int = Field(0, ge=0)
    clear_existing: bool = False


class AutonomousCycleRequest(BaseModel):
    market_prices: Dict[str, float] = Field(default_factory=dict)
    max_orders: Optional[int] = Field(default=None, ge=1, le=100)
    cycle_notional_limit: Optional[float] = Field(default=None, ge=0)
    participation_rate: Optional[float] = Field(default=None, gt=0, le=1)
    queue_item_limit: Optional[int] = Field(default=None, ge=1, le=100)
    approver: str = Field(default='autonomous_execution_layer')
    notes: str = Field(default='controlled autonomous execution cycle')
    allow_when_disabled: bool = False
    ingest_if_empty: bool = True


class AutonomousResetRequest(BaseModel):
    approver: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
    clear_escalations: bool = False
