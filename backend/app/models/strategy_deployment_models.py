from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DeploymentProfile(BaseModel):
    strategy_id: Optional[str] = None
    name: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    asset_class: str = Field(..., min_length=1)
    preferred_regimes: List[str] = Field(default_factory=lambda: ['neutral'])
    warmup_required: bool = False
    deployment_readiness: float = Field(0.85, ge=0, le=1.25)
    max_live_weight: float = Field(0.25, gt=0, le=1)
    min_ticket_pct: float = Field(0.05, ge=0, le=1)
    allowed_brokers: List[Literal['paper', 'binance', 'ibkr']] = Field(default_factory=lambda: ['paper'])
    status: Literal['standby', 'active', 'retired'] = 'standby'
    enabled: bool = True


class DeploymentEvaluationRequest(BaseModel):
    regime: Optional[Literal['bull', 'neutral', 'range', 'bear', 'stress']] = None
    liquidity_state: Optional[Literal['normal', 'tight', 'stressed']] = None
    max_concurrent_strategies: Optional[int] = Field(default=None, ge=1, le=20)
    allocation_plan: Optional[dict] = None


class DeploymentApprovalRequest(BaseModel):
    approver: str = Field(..., min_length=1)
    notes: str = Field(default='approved')
    plan: Optional[dict] = None


class DeploymentRegimeSwitchRequest(BaseModel):
    regime: Literal['bull', 'neutral', 'range', 'bear', 'stress']
    liquidity_state: Literal['normal', 'tight', 'stressed'] = 'normal'
    force_redeploy: bool = False
