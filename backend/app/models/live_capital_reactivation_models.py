from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class LiveCapitalReactivationConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_reauthorization_execution: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_strategy_profile_match: Optional[bool] = None
    require_treasury_capacity: Optional[bool] = None
    allow_live_mode: Optional[bool] = None
    max_reactivation_cases: Optional[int] = Field(default=None, ge=25, le=5000)
    max_reentry_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class LiveCapitalReactivationSyncRequest(BaseModel):
    source: str = Field(default='manual')


class LiveCapitalReactivationRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    reauthorization_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    symbol: str = Field(default='')
    broker: str = Field(default='')
    requested_capital: float = Field(default=0.0, ge=0)
    requested_weight: float = Field(default=0.0, ge=0, le=1)
    reentry_reason: str = Field(default='')
    notes: str = Field(default='')


class LiveCapitalReactivationApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reactivation_id: str = Field(..., min_length=1)
    approved_capital: float = Field(default=0.0, ge=0)
    approved_weight: float = Field(default=0.0, ge=0, le=1)
    mode: str = Field(default='paper')
    approval_notes: str = Field(default='')


class LiveCapitalReactivationExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reactivation_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='paper')
    capital_activated: float = Field(default=0.0, ge=0)
    release_to: str = Field(default='execution_queue')
    result_summary: str = Field(default='')


class LiveCapitalReactivationClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reactivation_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class LiveCapitalReactivationResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
