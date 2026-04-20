from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RegulatoryDisclosureConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    require_published_binder: Optional[bool] = None
    require_retrieval_packet: Optional[bool] = None
    require_supervisory_channel: Optional[bool] = None
    require_delivery_receipt: Optional[bool] = None
    require_primary_acknowledgement_before_close: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    primary_supervisor: Optional[str] = Field(default=None, min_length=1)
    default_delivery_channel: Optional[str] = Field(default=None, min_length=1)
    retention_days: Optional[int] = Field(default=None, ge=30)
    sync_after_configure: bool = True


class RegulatoryDisclosureSyncRequest(BaseModel):
    source: str = Field(default='manual')


class RegulatoryDisclosureRegisterRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    published_binder_id: str = Field(..., min_length=1)
    operations: str = Field(..., min_length=1)
    compliance: str = Field(..., min_length=1)
    supervisor: str = Field(default='')
    delivery_channel: str = Field(default='')
    notes: str = Field(default='')


class RegulatoryDisclosureReceiptRequest(BaseModel):
    delivery_case_id: str = Field(..., min_length=1)
    receiver: str = Field(..., min_length=1)
    receipt_reference: str = Field(default='')
    delivery_channel: str = Field(default='')


class SupervisoryAcknowledgementRequest(BaseModel):
    delivery_case_id: str = Field(..., min_length=1)
    acknowledger: str = Field(..., min_length=1)
    outcome: str = Field(default='accepted', min_length=1)
    reference: str = Field(default='')
    notes: str = Field(default='')


class RegulatoryDisclosureResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
