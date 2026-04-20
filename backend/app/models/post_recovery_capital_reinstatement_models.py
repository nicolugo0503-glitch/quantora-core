from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class PostRecoveryCapitalReinstatementConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_recovery_execution_for_approval: Optional[bool] = None
    require_closed_action_for_close: Optional[bool] = None
    require_risk_clearance_for_execution: Optional[bool] = None
    require_positive_capital_recovered: Optional[bool] = None
    require_treasury_capacity: Optional[bool] = None
    max_reauthorization_cases: Optional[int] = Field(default=None, ge=25, le=5000)
    max_reinstatement_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class PostRecoveryCapitalReinstatementSyncRequest(BaseModel):
    source: str = Field(default='manual')


class PostRecoveryCapitalReauthorizationRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    action_id: str = Field(..., min_length=1)
    cycle_id: str = Field(default='')
    case_id: str = Field(default='')
    resolution_id: str = Field(default='')
    target_strategy: str = Field(default='')
    target_broker: str = Field(default='')
    requested_capital: float = Field(default=0.0, ge=0)
    reinstatement_pct: float = Field(default=0.0, ge=0, le=100)
    rationale: str = Field(default='')
    notes: str = Field(default='')


class PostRecoveryCapitalReinstatementApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reauthorization_id: str = Field(..., min_length=1)
    approved_capital: float = Field(default=0.0, ge=0)
    approval_notes: str = Field(default='')


class PostRecoveryCapitalReinstatementExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reauthorization_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='controlled')
    capital_reinstated: float = Field(default=0.0, ge=0)
    destination_account: str = Field(default='broker_buffer')
    result_summary: str = Field(default='')


class PostRecoveryCapitalReauthorizationClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reauthorization_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class PostRecoveryCapitalReinstatementResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
