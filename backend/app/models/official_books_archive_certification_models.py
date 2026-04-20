from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class OfficialBooksConfigurationRequest(BaseModel):
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)
    require_closed_period: Optional[bool] = None
    require_notice_finalization: Optional[bool] = None
    require_archive_certification: Optional[bool] = None
    require_zero_open_breaks: Optional[bool] = None
    require_controller_signoff: Optional[bool] = None
    require_operations_signoff: Optional[bool] = None
    retain_release_payload_days: Optional[int] = Field(default=None, ge=30)
    archive_channel: Optional[str] = Field(default=None, min_length=1)
    auto_sync_sources: Optional[bool] = None
    sync_after_configure: bool = True


class OfficialBooksSyncRequest(BaseModel):
    source: str = Field(default='manual')


class OfficialBooksRegisterRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    period_close_id: str = Field(..., min_length=1)
    controller: str = Field(default='')
    operations: str = Field(default='')
    notes: str = Field(default='')


class ArchiveCertificationRequest(BaseModel):
    books_release_id: str = Field(..., min_length=1)
    certifier: str = Field(..., min_length=1)
    artifact_count: int = Field(default=0, ge=0)
    checksum_manifest_id: str = Field(default='')


class OfficialBooksReleaseRequest(BaseModel):
    books_release_id: str = Field(..., min_length=1)
    approver: str = Field(..., min_length=1)


class OfficialBooksResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
