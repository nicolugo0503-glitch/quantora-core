from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class InvestorCashConfirmationConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    require_bank_instruction_verified: Optional[bool] = None
    require_statement_alignment: Optional[bool] = None
    require_transfer_approved: Optional[bool] = None
    require_treasury_capacity: Optional[bool] = None
    require_dual_ack: Optional[bool] = None
    release_authority_ttl_seconds: Optional[int] = Field(default=None, ge=60)
    max_unresolved_exceptions: Optional[int] = Field(default=None, ge=0)
    auto_sync_treasury: Optional[bool] = None
    sync_after_configure: bool = True


class InvestorCashConfirmationSyncRequest(BaseModel):
    source: str = Field(default='manual')


class InvestorRegistrationRequest(BaseModel):
    investor_id: str = Field(..., min_length=1)
    investor_name: str = Field(..., min_length=1)
    bank_instruction_verified: bool = False
    statement_alignment_status: str = Field(default='pending', min_length=1)
    preferred_currency: str = Field(default='USD', min_length=3, max_length=8)
    cash_confirmation_contact: str = Field(default='')
    status: str = Field(default='active', min_length=1)


class InvestorReleaseRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    transfer_id: str = Field(..., min_length=1)
    investor_id: str = Field(..., min_length=1)
    amount: Optional[float] = Field(default=None, gt=0)
    dealing_reference: str = Field(default='')
    statement_cycle_id: str = Field(default='')
    notes: str = Field(default='')


class InvestorCashAcknowledgementRequest(BaseModel):
    release_request_id: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    ack_type: str = Field(default='ops', min_length=1)
    note: str = Field(default='')


class InvestorReleaseAuthorizeRequest(BaseModel):
    release_request_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class InvestorCashConfirmationResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
    clear_audit: bool = False
