from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DistributionPayablesConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    require_registered_investor: Optional[bool] = None
    require_statement_cycle: Optional[bool] = None
    require_dual_attestation: Optional[bool] = None
    require_treasury_capacity: Optional[bool] = None
    require_batch_authority: Optional[bool] = None
    require_transfer_approved: Optional[bool] = None
    require_positive_distributable_return: Optional[bool] = None
    max_unresolved_breaks: Optional[int] = Field(default=None, ge=0)
    max_distribution_pct_of_equity: Optional[float] = Field(default=None, ge=0)
    distribution_amount_tolerance: Optional[float] = Field(default=None, ge=0)
    release_authority_ttl_seconds: Optional[int] = Field(default=None, ge=60)
    auto_sync_sources: Optional[bool] = None
    sync_after_configure: bool = True


class DistributionPayablesSyncRequest(BaseModel):
    source: str = Field(default='manual')


class DistributionAllocationLine(BaseModel):
    investor_id: str = Field(..., min_length=1)
    investor_name: str = Field(default='')
    amount: Optional[float] = Field(default=None, ge=0)
    weight: Optional[float] = Field(default=None, ge=0)
    bank_destination: str = Field(default='investor_distribution_bank')
    notes: str = Field(default='')


class DistributionBatchRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    batch_name: str = Field(..., min_length=1)
    distribution_type: str = Field(default='profit_distribution', min_length=1)
    total_amount: float = Field(..., gt=0)
    currency: str = Field(default='USD', min_length=3, max_length=8)
    period_id: str = Field(default='')
    statement_cycle_id: str = Field(default='')
    source_nav_date: str = Field(default='')
    payable_basis: str = Field(default='pro_rata', min_length=1)
    notes: str = Field(default='')
    allocations: List[DistributionAllocationLine] = Field(default_factory=list)


class DistributionAttestationRequest(BaseModel):
    batch_id: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    attestation_type: str = Field(default='ops', min_length=1)
    note: str = Field(default='')


class DistributionBatchAuthorizeRequest(BaseModel):
    batch_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class DistributionTransferBindRequest(BaseModel):
    batch_id: str = Field(..., min_length=1)
    transfer_id: str = Field(..., min_length=1)
    investor_id: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)
    line_id: str = Field(default='')
    note: str = Field(default='')


class DistributionPayableAuthorizeRequest(BaseModel):
    transfer_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class DistributionExecutionRecordRequest(BaseModel):
    transfer_id: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)
    note: str = Field(default='')


class DistributionResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
    clear_audit: bool = False
