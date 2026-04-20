from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class IntercompanyLedgerConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    auto_sync_sources: Optional[bool] = None
    require_approval: Optional[bool] = None
    approval_threshold: Optional[float] = Field(default=None, ge=0)
    require_treasury_capacity: Optional[bool] = None
    require_disclosure_acknowledgement: Optional[bool] = None
    default_settlement_route: Optional[str] = Field(default=None, min_length=1)
    retention_days: Optional[int] = Field(default=None, ge=30)
    sync_after_configure: bool = True


class IntercompanyLedgerSyncRequest(BaseModel):
    source: str = Field(default='manual')


class IntercompanyFlowRegisterRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    from_entity: str = Field(..., min_length=1)
    to_entity: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    purpose: str = Field(..., min_length=1)
    flow_type: str = Field(default='capital_transfer', min_length=1)
    effective_date: str = Field(default='')
    currency: str = Field(default='')
    treasury_transfer_id: str = Field(default='')
    settlement_id: str = Field(default='')
    reference_id: str = Field(default='')
    legal_entity_id: str = Field(default='')
    counterparty_entity_id: str = Field(default='')
    fund_id: str = Field(default='')
    spv_id: str = Field(default='')
    strategy_id: str = Field(default='')
    jurisdiction: str = Field(default='')
    notes: str = Field(default='')


class IntercompanyFlowApproveRequest(BaseModel):
    flow_case_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)
    approval_memo: str = Field(default='')


class IntercompanyFlowPostRequest(BaseModel):
    flow_case_id: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)
    debit_account: str = Field(default='due_from_affiliate')
    credit_account: str = Field(default='due_to_affiliate')
    posting_memo: str = Field(default='')


class IntercompanyFlowSettleRequest(BaseModel):
    flow_case_id: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)
    treasury_transfer_id: str = Field(default='')
    settlement_route: str = Field(default='')
    settlement_memo: str = Field(default='')


class IntercompanyLedgerResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
