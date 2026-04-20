from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class InstitutionalBreachExceptionConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_risk_sync: Optional[bool] = None
    require_settlement_sync: Optional[bool] = None
    require_charter_directive_context: Optional[bool] = None
    require_supervisory_escalation_for_severe: Optional[bool] = None
    severe_alignment_threshold: Optional[float] = Field(default=None, ge=0, le=100)
    default_resolution_sla_hours: Optional[int] = Field(default=None, ge=1, le=720)
    max_cases_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_resolutions_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_escalations_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class InstitutionalBreachExceptionSyncRequest(BaseModel):
    source: str = Field(default='manual')


class InstitutionalBreachCaseRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    breach_type: str = Field(default='MANDATE_EXCEPTION')
    severity: str = Field(default='medium')
    source_system: str = Field(default='institutional-charter')
    directive_id: str = Field(default='')
    target_strategy: str = Field(default='')
    requested_action: str = Field(default='')
    alignment_score: float = Field(default=0.0, ge=0, le=100)
    root_cause: str = Field(default='')
    summary: str = Field(default='')
    required_resolution_sla_hours: int = Field(default=24, ge=1, le=720)
    needs_supervisory_review: bool = False
    tags: List[str] = Field(default_factory=list)


class InstitutionalBreachEscalationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    escalation_level: str = Field(default='operations')
    reason: str = Field(default='')


class InstitutionalExceptionResolutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    resolution_type: str = Field(default='override')
    approved: bool = False
    exception_scope: str = Field(default='')
    control_actions: List[str] = Field(default_factory=list)
    expiry_hours: int = Field(default=0, ge=0, le=720)
    notes: str = Field(default='')


class InstitutionalBreachExceptionResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
