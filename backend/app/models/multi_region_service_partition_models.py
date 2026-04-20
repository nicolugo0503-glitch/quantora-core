from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class MultiRegionServicePartitionConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_shared_services_execution: Optional[bool] = None
    require_compliance_clearance: Optional[bool] = None
    require_treasury_capacity: Optional[bool] = None
    allow_live_partition_execution: Optional[bool] = None
    default_region_budget_limit: Optional[float] = Field(default=None, ge=0)
    max_expansion_cases: Optional[int] = Field(default=None, ge=25, le=5000)
    max_partition_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class MultiRegionServicePartitionSyncRequest(BaseModel):
    source: str = Field(default='manual')


class MultiRegionServicePartitionRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    region_name: str = Field(..., min_length=1)
    operating_model: str = Field(default='regional-hub')
    jurisdictions: List[str] = Field(default_factory=list)
    service_partitions: List[str] = Field(default_factory=list)
    regional_budget: float = Field(default=0.0, ge=0)
    budget_limit: float = Field(default=0.0, ge=0)
    service_event_id: str = Field(default='')
    directive_id: str = Field(default='')
    operating_mode: str = Field(default='paper')
    notes: str = Field(default='')


class MultiRegionServicePartitionApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    expansion_case_id: str = Field(..., min_length=1)
    approved_budget: float = Field(default=0.0, ge=0)
    approval_mode: str = Field(default='paper')
    approval_notes: str = Field(default='')


class MultiRegionServicePartitionExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    expansion_case_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='paper')
    partition_registry: str = Field(default='regional_service_registry')
    jurisdiction_count: int = Field(default=0, ge=0)
    result_summary: str = Field(default='')


class MultiRegionServicePartitionClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    expansion_case_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class MultiRegionServicePartitionResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
