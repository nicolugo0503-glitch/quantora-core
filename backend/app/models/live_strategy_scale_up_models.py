from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class LiveStrategyScaleUpConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_reentry_execution: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_treasury_capacity: Optional[bool] = None
    require_positive_performance_signal: Optional[bool] = None
    default_max_ramp_steps: Optional[int] = Field(default=None, ge=1, le=25)
    default_max_ramp_pct: Optional[float] = Field(default=None, ge=0, le=1)
    allow_live_scale_up: Optional[bool] = None
    max_scale_cases: Optional[int] = Field(default=None, ge=25, le=5000)
    max_ramp_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class LiveStrategyScaleUpSyncRequest(BaseModel):
    source: str = Field(default='manual')


class LiveStrategyScaleUpRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    reentry_event_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    symbol: str = Field(default='')
    broker: str = Field(default='')
    current_capital: float = Field(default=0.0, ge=0)
    requested_ramp_capital: float = Field(default=0.0, ge=0)
    requested_target_weight: float = Field(default=0.0, ge=0, le=1)
    ramp_steps: int = Field(default=0, ge=0, le=25)
    max_ramp_pct: float = Field(default=0.0, ge=0, le=1)
    ramp_reason: str = Field(default='')
    notes: str = Field(default='')


class LiveStrategyScaleUpApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    scale_case_id: str = Field(..., min_length=1)
    approved_ramp_capital: float = Field(default=0.0, ge=0)
    approved_target_weight: float = Field(default=0.0, ge=0, le=1)
    mode: str = Field(default='paper')
    approval_notes: str = Field(default='')


class LiveStrategyScaleUpExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    scale_case_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='paper')
    ramp_capital_deployed: float = Field(default=0.0, ge=0)
    target_weight: float = Field(default=0.0, ge=0, le=1)
    release_to: str = Field(default='allocation_engine')
    result_summary: str = Field(default='')


class LiveStrategyScaleUpClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    scale_case_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class LiveStrategyScaleUpResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
