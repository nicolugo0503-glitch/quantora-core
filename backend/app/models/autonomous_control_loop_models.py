
from __future__ import annotations

from typing import Dict, Optional
from pydantic import BaseModel, Field


class AutonomousControlLoopConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    auto_ingest_release_queue: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_liquidity_capacity: Optional[bool] = None
    require_intercompany_clear: Optional[bool] = None
    require_positive_performance_bias: Optional[bool] = None
    minimum_available_liquidity: Optional[float] = Field(default=None, ge=0)
    minimum_cumulative_return_pct: Optional[float] = None
    max_cycles_to_keep: Optional[int] = Field(default=None, ge=10, le=1000)
    sync_after_configure: bool = True


class AutonomousControlLoopSyncRequest(BaseModel):
    source: str = Field(default='manual')


class AutonomousControlLoopPlanRequest(BaseModel):
    operator: str = Field(default='system')
    source: str = Field(default='manual')
    ingest_if_empty: bool = True
    queue_index: int = Field(default=0, ge=0)
    max_orders: int = Field(default=3, ge=1, le=25)
    cycle_notional_limit: float = Field(default=250000.0, ge=0)
    market_prices: Dict[str, float] = Field(default_factory=dict)


class AutonomousControlLoopExecuteRequest(BaseModel):
    operator: str = Field(default='system')
    source: str = Field(default='manual')
    use_latest_plan: bool = True
    plan_id: str = Field(default='')
    market_prices: Dict[str, float] = Field(default_factory=dict)


class AutonomousControlLoopResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
