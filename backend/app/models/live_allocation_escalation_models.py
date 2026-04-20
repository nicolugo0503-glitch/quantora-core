from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class LiveAllocationEscalationConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_scale_execution: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_capacity_headroom: Optional[bool] = None
    require_charter_alignment: Optional[bool] = None
    allow_live_escalation: Optional[bool] = None
    default_capacity_ceiling_pct: Optional[float] = Field(default=None, ge=0, le=1)
    default_escalation_step_pct: Optional[float] = Field(default=None, ge=0, le=1)
    max_escalation_cases: Optional[int] = Field(default=None, ge=25, le=5000)
    max_escalation_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class LiveAllocationEscalationSyncRequest(BaseModel):
    source: str = Field(default='manual')


class LiveAllocationEscalationRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    scale_event_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    symbol: str = Field(default='')
    broker: str = Field(default='')
    current_weight: float = Field(default=0.0, ge=0, le=1)
    requested_total_weight: float = Field(default=0.0, ge=0, le=1)
    requested_incremental_capital: float = Field(default=0.0, ge=0)
    capacity_ceiling_pct: float = Field(default=0.0, ge=0, le=1)
    escalation_step_pct: float = Field(default=0.0, ge=0, le=1)
    allocation_reason: str = Field(default='')
    directive_id: str = Field(default='')
    notes: str = Field(default='')


class LiveAllocationEscalationApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    escalation_case_id: str = Field(..., min_length=1)
    approved_total_weight: float = Field(default=0.0, ge=0, le=1)
    approved_incremental_capital: float = Field(default=0.0, ge=0)
    mode: str = Field(default='paper')
    approval_notes: str = Field(default='')


class LiveAllocationEscalationExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    escalation_case_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='paper')
    incremental_capital_deployed: float = Field(default=0.0, ge=0)
    total_weight: float = Field(default=0.0, ge=0, le=1)
    release_to: str = Field(default='allocation_engine')
    result_summary: str = Field(default='')


class LiveAllocationEscalationClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    escalation_case_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class LiveAllocationEscalationResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
