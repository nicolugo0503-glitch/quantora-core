from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class InvestorExitFinalizationConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    require_executed_transfer: Optional[bool] = None
    require_release_authority: Optional[bool] = None
    require_dual_attestation: Optional[bool] = None
    require_reconciliation_clear: Optional[bool] = None
    require_cash_paid_match: Optional[bool] = None
    allow_in_kind_component: Optional[bool] = None
    amount_tolerance: Optional[float] = Field(default=None, ge=0)
    max_unresolved_settlement_breaks: Optional[int] = Field(default=None, ge=0)
    exit_authority_ttl_seconds: Optional[int] = Field(default=None, ge=60)
    auto_sync_sources: Optional[bool] = None
    sync_after_configure: bool = True


class InvestorExitSyncRequest(BaseModel):
    source: str = Field(default='manual')


class InvestorExitCaseRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    transfer_id: str = Field(..., min_length=1)
    investor_id: str = Field(..., min_length=1)
    investor_name: str = Field(default='')
    gross_redemption_amount: Optional[float] = Field(default=None, gt=0)
    cash_paid_amount: Optional[float] = Field(default=None, ge=0)
    in_kind_amount: float = Field(default=0.0, ge=0)
    currency: str = Field(default='USD', min_length=3, max_length=8)
    capital_activity_id: str = Field(default='')
    statement_cycle_id: str = Field(default='')
    dealing_reference: str = Field(default='')
    notes: str = Field(default='')


class InvestorExitAttestationRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    attestation_type: str = Field(default='ops', min_length=1)
    note: str = Field(default='')


class InvestorExitAuthorizeRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class InvestorExitFinalizeRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)
    notes: str = Field(default='')


class InvestorExitFinalizationResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
    clear_audit: bool = False
