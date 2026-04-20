from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class MultiVehicleSharedServicesConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_vehicle_launch_execution: Optional[bool] = None
    require_charter_alignment: Optional[bool] = None
    allow_live_shared_services: Optional[bool] = None
    default_minimum_supported_vehicles: Optional[int] = Field(default=None, ge=1, le=1000)
    max_service_models: Optional[int] = Field(default=None, ge=25, le=5000)
    max_service_events: Optional[int] = Field(default=None, ge=25, le=5000)
    max_audit_events: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class MultiVehicleSharedServicesSyncRequest(BaseModel):
    source: str = Field(default='manual')


class MultiVehicleSharedServicesRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    service_name: str = Field(..., min_length=1)
    service_type: str = Field(default='shared-services')
    operating_region: str = Field(default='global')
    supported_vehicle_types: List[str] = Field(default_factory=list)
    minimum_supported_vehicles: int = Field(default=2, ge=1)
    annual_budget: float = Field(default=0.0, ge=0)
    budget_source: str = Field(default='opex')
    service_scope: str = Field(default='')
    launch_event_id: str = Field(default='')
    directive_id: str = Field(default='')
    operating_mode: str = Field(default='paper')
    notes: str = Field(default='')


class MultiVehicleSharedServicesApprovalRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    service_model_id: str = Field(..., min_length=1)
    approved_budget: float = Field(default=0.0, ge=0)
    approval_mode: str = Field(default='paper')
    approval_notes: str = Field(default='')


class MultiVehicleSharedServicesExecutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    service_model_id: str = Field(..., min_length=1)
    execution_mode: str = Field(default='paper')
    service_destination: str = Field(default='shared_services_registry')
    vehicle_count: int = Field(default=0, ge=0)
    result_summary: str = Field(default='')


class MultiVehicleSharedServicesClosureRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    service_model_id: str = Field(..., min_length=1)
    closure_notes: str = Field(default='')


class MultiVehicleSharedServicesResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
