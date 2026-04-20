from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class GovernanceBinderConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    require_official_books_release: Optional[bool] = None
    require_archive_certification: Optional[bool] = None
    require_retrieval_packet_assembly: Optional[bool] = None
    require_regulator_channel: Optional[bool] = None
    require_operations_attestation: Optional[bool] = None
    require_compliance_attestation: Optional[bool] = None
    retain_packet_days: Optional[int] = Field(default=None, ge=30)
    binder_channel: Optional[str] = Field(default=None, min_length=1)
    regulator_channel: Optional[str] = Field(default=None, min_length=1)
    auto_sync_sources: Optional[bool] = None
    sync_after_configure: bool = True


class GovernanceBinderSyncRequest(BaseModel):
    source: str = Field(default='manual')


class GovernanceBinderRegisterRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    official_release_id: str = Field(..., min_length=1)
    operations: str = Field(default='')
    compliance: str = Field(default='')
    notes: str = Field(default='')


class GovernanceRetrievalPacketRequest(BaseModel):
    publication_case_id: str = Field(..., min_length=1)
    assembler: str = Field(..., min_length=1)
    artifact_count: int = Field(default=0, ge=0)
    packet_manifest_id: str = Field(default='')
    regulator_channel: str = Field(default='')


class GovernanceBinderPublishRequest(BaseModel):
    publication_case_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class GovernanceBinderResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
