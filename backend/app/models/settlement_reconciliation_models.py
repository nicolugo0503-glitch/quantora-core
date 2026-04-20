from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SettlementControlConfigurationRequest(BaseModel):
    auto_ingest_fills: Optional[bool] = None
    auto_reconcile_after_confirm: Optional[bool] = None
    position_tolerance_qty: Optional[float] = Field(default=None, ge=0)
    cash_tolerance: Optional[float] = Field(default=None, ge=0)
    notional_tolerance: Optional[float] = Field(default=None, ge=0)
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=8)


class SettlementIngestRequest(BaseModel):
    auto_process: bool = False
    operator: str = Field(default='settlement_control_layer')
    notes: str = Field(default='execution fill ingestion')


class SettlementConfirmRequest(BaseModel):
    settlement_ids: List[str] = Field(default_factory=list)
    operator: str = Field(..., min_length=1)
    cash_confirmed: bool = True
    custody_confirmed: bool = True
    notes: str = Field(default='manual settlement confirmation')


class ReconciliationRunRequest(BaseModel):
    broker_positions: Dict[str, float] = Field(default_factory=dict)
    broker_cash_balance: Optional[float] = None
    operator: str = Field(default='settlement_control_layer')
    notes: str = Field(default='manual reconciliation run')
    auto_ingest: bool = True


class SettlementResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
    clear_audit: bool = False
