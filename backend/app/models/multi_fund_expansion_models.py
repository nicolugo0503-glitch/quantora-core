from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class MultiFundExpansionConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_escalation_execution: Optional[bool] = None
    require_risk_clearance: Optional[bool] = None
    require_treasury_capacity: Optional[bool] = None
    require_charter_alignment: Optional[bool] = None
    require_vehicle_readiness: Optional[bool] = None
    allow_live_launch: Optional[bool] = None
    default_seed_capital_floor: Optional[float] = Field(default=None, ge=0)
    default_capacity_target: Optional[float] = Field(default=None, ge=0, le=1)
    max_launch_cases: Optional[int] = Field(default=None, ge=25, le=5000)
    max_launch_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class MultiFundExpansionSyncRequest(BaseModel):
    source: str = Field(default='manual')


class MultiFundExpansionRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    vehicle_name: str = Field(..., min_length=1)
    vehicle_type: str = Field(default='fund')
    jurisdiction: str = Field(default='')
    launch_reason: str = Field(default='')
    strategy_scope: str = Field(default='')
    seed_capital_required: float = Field(default=0.0, ge=0)
    seed_capital_floor: float = Field(default=0.0, ge=0)
    target_capacity_pct: float = Field(default=0.0, ge=0, le=1)
    escalation_event_id: str = Field(default='')
    directive_id: str = Field(default='')
    launch_mode: str = Field(default='paper')
    notes: str = Field(default='')


class MultiFundExpansionApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    launch_case_id: str = Field(..., min_length=1)
    approved_seed_capital: float = Field(default=0.0, ge=0)
    approved_vehicle_code: str = Field(default='')
    approval_mode: str = Field(default='paper')
    approval_notes: str = Field(default='')


class MultiFundExpansionExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    launch_case_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='paper')
    vehicle_code: str = Field(default='')
    seed_capital_deployed: float = Field(default=0.0, ge=0)
    launch_destination: str = Field(default='vehicle_registry')
    result_summary: str = Field(default='')


class MultiFundExpansionClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    launch_case_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class MultiFundExpansionResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
