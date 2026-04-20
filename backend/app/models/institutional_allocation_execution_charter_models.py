from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class InstitutionalAllocationExecutionCharterConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_arbitration_context: Optional[bool] = None
    require_committee_alignment: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_liquidity_support: Optional[bool] = None
    minimum_policy_alignment_score: Optional[float] = Field(default=None, ge=0, le=100)
    minimum_mandate_alignment_score: Optional[float] = Field(default=None, ge=0, le=100)
    max_charters_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_mandates_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_directives_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class InstitutionalAllocationExecutionCharterSyncRequest(BaseModel):
    source: str = Field(default='manual')


class InstitutionalExecutionCharterRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    charter_scope: str = Field(default='INSTITUTIONAL_EXECUTION_CHARTER')
    summary: str = Field(default='')
    target_strategy: str = Field(default='')
    allowed_actions: List[str] = Field(default_factory=list)
    blocked_actions: List[str] = Field(default_factory=list)
    max_notional: float = Field(default=250000.0, ge=0)
    max_capital_delta_pct: float = Field(default=0.12)
    jurisdiction: str = Field(default='')
    entity_scope: str = Field(default='')
    active: bool = True
    tags: List[str] = Field(default_factory=list)


class InstitutionalMandateRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    charter_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    summary: str = Field(default='')
    target_strategy: str = Field(default='')
    allowed_actions: List[str] = Field(default_factory=list)
    blocked_actions: List[str] = Field(default_factory=list)
    minimum_mandate_alignment_score: float = Field(default=82.0, ge=0, le=100)
    max_notional: Optional[float] = Field(default=None, ge=0)
    max_capital_delta_pct: Optional[float] = None
    require_explicit_committee_memory: bool = False
    active: bool = True
    tags: List[str] = Field(default_factory=list)


class InstitutionalMandateEnforcementRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    decision_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    execution_action: str = Field(default='')
    target_strategy: str = Field(default='')
    proposed_notional: Optional[float] = Field(default=None, ge=0)
    capital_delta_pct: Optional[float] = None
    mandate_alignment_score: float = Field(default=85.0, ge=0, le=100)
    instruction: str = Field(default='')


class InstitutionalAllocationExecutionCharterResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
