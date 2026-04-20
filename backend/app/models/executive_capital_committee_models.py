from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ExecutiveCapitalCommitteeConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_liquidity_support: Optional[bool] = None
    require_control_loop_context: Optional[bool] = None
    require_committee_approval: Optional[bool] = None
    minimum_committee_score: Optional[float] = Field(default=None, ge=0, le=100)
    minimum_memory_confidence_score: Optional[float] = Field(default=None, ge=0, le=100)
    minimum_available_liquidity: Optional[float] = Field(default=None, ge=0)
    operator_review_notional_threshold: Optional[float] = Field(default=None, ge=0)
    max_memories_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_decisions_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class ExecutiveCapitalCommitteeSyncRequest(BaseModel):
    source: str = Field(default='manual')


class ExecutiveCapitalMemoryRecordRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    decision_scope: str = Field(default='EXECUTIVE_CAPITAL_DECISION')
    summary: str = Field(default='')
    outcome_summary: str = Field(default='')
    tags: List[str] = Field(default_factory=list)
    memory_confidence_score: float = Field(default=80.0, ge=0, le=100)
    outcome_quality_score: float = Field(default=80.0, ge=0, le=100)
    linked_decision_id: str = Field(default='')


class ExecutiveCapitalCommitteeProposalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    decision_scope: str = Field(default='EXECUTIVE_CAPITAL_DECISION')
    summary: str = Field(default='')
    requested_action: str = Field(default='observe')
    target_strategy: str = Field(default='')
    proposed_notional: float = Field(default=0.0, ge=0)
    capital_delta_pct: float = Field(default=0.0)
    conviction_score: float = Field(default=80.0, ge=0, le=100)
    scenario_coverage_score: float = Field(default=80.0, ge=0, le=100)
    execution_feasibility_score: float = Field(default=80.0, ge=0, le=100)
    policy_alignment_score: float = Field(default=80.0, ge=0, le=100)
    tags: List[str] = Field(default_factory=list)
    memory_limit: int = Field(default=5, ge=1, le=20)


class ExecutiveCapitalCommitteeApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    proposal_id: str = Field(..., min_length=1)
    outcome: str = Field(default='approve')
    rationale: str = Field(default='')


class ExecutiveCapitalCommitteeResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
