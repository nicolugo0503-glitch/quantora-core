from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ExecutiveScenarioArbitrationConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_committee_context: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_safe_mode_for_live_override: Optional[bool] = None
    require_policy_alignment: Optional[bool] = None
    minimum_policy_alignment_score: Optional[float] = Field(default=None, ge=0, le=100)
    minimum_scenario_resilience_score: Optional[float] = Field(default=None, ge=0, le=100)
    minimum_available_liquidity: Optional[float] = Field(default=None, ge=0)
    max_capital_delta_pct: Optional[float] = None
    max_live_notional_without_override: Optional[float] = Field(default=None, ge=0)
    max_scenarios_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_decisions_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class ExecutiveScenarioArbitrationSyncRequest(BaseModel):
    source: str = Field(default='manual')


class AllocationPolicyRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    policy_scope: str = Field(default='CAPITAL_ALLOCATION_POLICY')
    summary: str = Field(default='')
    target_strategy: str = Field(default='')
    allowed_actions: List[str] = Field(default_factory=list)
    blocked_actions: List[str] = Field(default_factory=list)
    max_capital_delta_pct: float = Field(default=0.12)
    max_notional: float = Field(default=250000.0, ge=0)
    minimum_policy_alignment_score: float = Field(default=85.0, ge=0, le=100)
    minimum_scenario_resilience_score: float = Field(default=78.0, ge=0, le=100)
    jurisdiction: str = Field(default='')
    entity_scope: str = Field(default='')
    active: bool = True
    tags: List[str] = Field(default_factory=list)


class ExecutiveScenarioArbitrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    scenario_scope: str = Field(default='EXECUTIVE_SCENARIO_ARBITRATION')
    summary: str = Field(default='')
    requested_action: str = Field(..., min_length=1)
    target_strategy: str = Field(default='')
    proposed_notional: float = Field(default=0.0, ge=0)
    capital_delta_pct: float = Field(default=0.0)
    policy_alignment_score: float = Field(default=85.0, ge=0, le=100)
    scenario_resilience_score: float = Field(default=80.0, ge=0, le=100)
    downside_risk_score: float = Field(default=40.0, ge=0, le=100)
    liquidity_coverage_score: float = Field(default=80.0, ge=0, le=100)
    safe_mode_override_requested: bool = False
    committee_decision_id: str = Field(default='')
    rationale: str = Field(default='')
    tags: List[str] = Field(default_factory=list)


class AllocationPolicyEnforcementRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    decision_id: str = Field(..., min_length=1)
    enforcement_action: str = Field(default='issue_directive')
    instruction: str = Field(default='')


class ExecutiveScenarioArbitrationResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
