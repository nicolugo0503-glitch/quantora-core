from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StrategyAttributionEntry(BaseModel):
    strategy_id: str = Field(..., min_length=1)
    pnl: float = 0.0
    return_contribution_pct: float = Field(0.0, ge=-5, le=5)
    gross_exposure_pct: Optional[float] = Field(default=None, ge=0, le=5)


class NavSnapshotRequest(BaseModel):
    as_of_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    equity: float = Field(..., gt=0)
    nav_per_unit: Optional[float] = Field(default=None, gt=0)
    net_flow: float = 0.0
    gross_exposure_pct: float = Field(0.0, ge=0, le=5)
    net_exposure_pct: float = Field(0.0, ge=-5, le=5)
    cash_pct: Optional[float] = Field(default=None, ge=0, le=5)
    strategy_attribution: List[StrategyAttributionEntry] = Field(default_factory=list)


class PerformanceConfigurationRequest(BaseModel):
    benchmark_rate_annual: Optional[float] = Field(default=None, ge=-1, le=1)
    minimum_acceptable_return_annual: Optional[float] = Field(default=None, ge=-1, le=1)
    target_volatility_annual: Optional[float] = Field(default=None, ge=0, le=5)
    trading_days_annual: Optional[int] = Field(default=None, ge=1, le=366)


class PerformanceRecomputeRequest(BaseModel):
    benchmark_rate_annual: Optional[float] = Field(default=None, ge=-1, le=1)
    minimum_acceptable_return_annual: Optional[float] = Field(default=None, ge=-1, le=1)
    sync_risk: bool = True
