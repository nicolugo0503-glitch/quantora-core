from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class AutonomousRecoveryConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_breach_sync: Optional[bool] = None
    require_risk_clearance_for_execute: Optional[bool] = None
    require_supervisory_resolution_for_severe_cases: Optional[bool] = None
    max_open_actions: Optional[int] = Field(default=None, ge=25, le=5000)
    max_recovery_cycles: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class AutonomousRecoverySyncRequest(BaseModel):
    source: str = Field(default='manual')


class RemediationActionRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    case_id: str = Field(default='')
    resolution_id: str = Field(default='')
    directive_id: str = Field(default='')
    title: str = Field(..., min_length=1)
    remediation_type: str = Field(default='containment')
    priority: str = Field(default='high')
    target_strategy: str = Field(default='')
    target_broker: str = Field(default='')
    requested_actions: List[str] = Field(default_factory=list)
    capital_at_risk: float = Field(default=0.0, ge=0)
    estimated_recovery_pct: float = Field(default=0.0, ge=0, le=100)
    requires_human_confirmation: bool = False
    notes: str = Field(default='')


class AutonomousRecoveryAuthorizationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    action_id: str = Field(..., min_length=1)
    recovery_instruction: str = Field(default='')
    required_confidence_score: float = Field(default=0.0, ge=0, le=100)


class AutonomousRecoveryExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    action_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='controlled')
    steps_executed: List[str] = Field(default_factory=list)
    recovered_capital: float = Field(default=0.0, ge=0)
    residual_risk_score: float = Field(default=0.0, ge=0, le=100)
    result_summary: str = Field(default='')


class AutonomousRecoveryClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    action_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class AutonomousRecoveryResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
