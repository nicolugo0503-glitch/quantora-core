from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TreasuryConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    reserve_floor: Optional[float] = Field(default=None, ge=0)
    reserve_buffer_pct: Optional[float] = Field(default=None, ge=0, le=1)
    min_operating_cash: Optional[float] = Field(default=None, ge=0)
    max_single_transfer_pct_of_available: Optional[float] = Field(default=None, ge=0, le=1)
    auto_sync_settlement: Optional[bool] = None
    settlement_haircut_pct: Optional[float] = Field(default=None, ge=0, le=1)
    rebalance_tolerance_pct: Optional[float] = Field(default=None, ge=0, le=1)
    sync_after_configure: bool = True


class TreasurySyncRequest(BaseModel):
    source: str = Field(default='manual')


class TreasuryStageTransferRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    transfer_type: str = Field(default='internal_rebalance', min_length=1)
    from_account: str = Field(default='broker_buffer', min_length=1)
    to_account: str = Field(default='')
    destination: str = Field(default='internal_treasury_route', min_length=1)
    currency: str = Field(default='USD', min_length=3, max_length=8)
    priority: str = Field(default='normal', min_length=1)
    purpose: str = Field(default='treasury cash mobility request', min_length=1)
    decision_id: str = Field(default='')
    allocation_id: str = Field(default='')
    settlement_dependency: str = Field(default='')
    investor_id: str = Field(default='')
    capital_activity_id: str = Field(default='')
    statement_cycle_id: str = Field(default='')


class TreasuryApproveTransferRequest(BaseModel):
    transfer_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)
    approval_notes: str = Field(default='')


class TreasuryExecuteTransferRequest(BaseModel):
    transfer_id: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)


class TreasuryRebalanceRequest(BaseModel):
    operator: str = Field(default='treasury_rebalance_engine', min_length=1)
    stage_actions: bool = False
    decision_id: str = Field(default='')


class TreasuryResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
    clear_audit: bool = False
