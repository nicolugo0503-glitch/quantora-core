from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class PeriodCloseDistributionConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    require_executed_payables: Optional[bool] = None
    require_notice_finalization: Optional[bool] = None
    require_zero_open_breaks: Optional[bool] = None
    require_period_attestation: Optional[bool] = None
    notice_delivery_channel: Optional[str] = Field(default=None, min_length=1)
    notice_ttl_seconds: Optional[int] = Field(default=None, ge=60)
    auto_sync_sources: Optional[bool] = None
    sync_after_configure: bool = True


class PeriodCloseDistributionSyncRequest(BaseModel):
    source: str = Field(default='manual')


class PeriodCloseRegisterRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    period_id: str = Field(..., min_length=1)
    statement_cycle_id: str = Field(default='')
    close_date: str = Field(default='')
    notes: str = Field(default='')
    ops_attested: bool = False
    finance_attested: bool = False


class PeriodCloseLedgerFinalizeRequest(BaseModel):
    period_close_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class PeriodCloseNoticeFinalizeRequest(BaseModel):
    period_close_id: str = Field(..., min_length=1)
    investor_id: str = Field(..., min_length=1)
    operator: str = Field(..., min_length=1)


class PeriodCloseFinalizeRequest(BaseModel):
    period_close_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class PeriodCloseResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
