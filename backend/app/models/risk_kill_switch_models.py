from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RiskThresholds(BaseModel):
    portfolio_drawdown_limit_pct: Optional[float] = Field(default=None, ge=0, le=1)
    strategy_drawdown_limit_pct: Optional[float] = Field(default=None, ge=0, le=1)
    daily_loss_limit_pct: Optional[float] = Field(default=None, ge=0, le=1)
    max_single_order_notional: Optional[float] = Field(default=None, ge=0)
    max_live_notional: Optional[float] = Field(default=None, ge=0)
    max_position_concentration_pct: Optional[float] = Field(default=None, ge=0, le=1)
    max_margin_usage_pct: Optional[float] = Field(default=None, ge=0, le=1)
    max_latency_ms: Optional[float] = Field(default=None, ge=0)


class RiskConfigurationRequest(BaseModel):
    armed: Optional[bool] = None
    safe_mode_on_trigger: Optional[bool] = None
    thresholds: RiskThresholds = Field(default_factory=RiskThresholds)


class RiskMetricsUpdateRequest(BaseModel):
    equity: Optional[float] = Field(default=None, ge=0)
    peak_equity: Optional[float] = Field(default=None, ge=0)
    portfolio_drawdown_pct: Optional[float] = Field(default=None, ge=0, le=1)
    strategy_drawdown_pct: Optional[float] = Field(default=None, ge=0, le=1)
    daily_loss_pct: Optional[float] = Field(default=None, ge=0, le=1)
    open_notional: Optional[float] = Field(default=None, ge=0)
    largest_position_pct: Optional[float] = Field(default=None, ge=0, le=1)
    margin_usage_pct: Optional[float] = Field(default=None, ge=0, le=1)
    latency_ms: Optional[float] = Field(default=None, ge=0)
    venue_connectivity_ok: Optional[bool] = None


class RiskControlActionRequest(BaseModel):
    approver: str = Field(..., min_length=1)
    reason: str = Field(default='manual action')
    safe_mode_on_trigger: Optional[bool] = None
    preserve_armed: bool = True


class KillSwitchOverrideRequest(BaseModel):
    approver: str = Field(..., min_length=1)
    ticket_id: str = Field(..., min_length=1)
    reason: str = Field(default='controlled override')
    keep_armed: bool = True
