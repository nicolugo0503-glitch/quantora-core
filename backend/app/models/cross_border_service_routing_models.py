from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class CrossBorderServiceRoutingConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_region_partition_execution: Optional[bool] = None
    require_compliance_clearance: Optional[bool] = None
    require_boundary_clearance: Optional[bool] = None
    allow_live_cross_border_execution: Optional[bool] = None
    default_route_notional_limit: Optional[float] = Field(default=None, ge=0)
    max_route_cases: Optional[int] = Field(default=None, ge=25, le=5000)
    max_routing_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class CrossBorderServiceRoutingSyncRequest(BaseModel):
    source: str = Field(default='manual')


class CrossBorderServiceRoutingRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    source_region: str = Field(..., min_length=1)
    destination_region: str = Field(..., min_length=1)
    source_jurisdiction: str = Field(..., min_length=1)
    destination_jurisdiction: str = Field(..., min_length=1)
    service_channels: List[str] = Field(default_factory=list)
    route_notional: float = Field(default=0.0, ge=0)
    route_limit: float = Field(default=0.0, ge=0)
    partition_event_id: str = Field(default='')
    compliance_decision_id: str = Field(default='')
    boundary_policy_id: str = Field(default='')
    execution_mode: str = Field(default='paper')
    notes: str = Field(default='')


class CrossBorderServiceRoutingApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    route_case_id: str = Field(..., min_length=1)
    approved_notional: float = Field(default=0.0, ge=0)
    boundary_clearance: bool = True
    approval_mode: str = Field(default='paper')
    approval_notes: str = Field(default='')


class CrossBorderServiceRoutingExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    route_case_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='paper')
    route_registry: str = Field(default='cross_border_service_registry')
    routed_channel_count: int = Field(default=0, ge=0)
    result_summary: str = Field(default='')


class CrossBorderServiceRoutingClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    route_case_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class CrossBorderServiceRoutingResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
