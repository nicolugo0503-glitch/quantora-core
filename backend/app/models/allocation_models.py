from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class StrategyProfile(BaseModel):
    strategy_id: Optional[str] = None
    name: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    asset_class: str = Field(..., min_length=1)
    signal_strength: float = Field(..., ge=0)
    conviction: float = Field(..., ge=0)
    liquidity_score: float = Field(..., ge=0)
    risk_budget: float = Field(..., ge=0)
    drawdown_pct: float = Field(0.0, ge=0)
    max_drawdown_limit: float = Field(..., gt=0)
    preferred_regimes: List[str] = Field(default_factory=lambda: ['neutral'])
    enabled: bool = True


class AllocationRecommendationRequest(BaseModel):
    capital: float = Field(..., gt=0)
    regime: Literal['bull', 'neutral', 'range', 'bear', 'stress'] = 'neutral'
    liquidity_state: Literal['normal', 'tight', 'stressed'] = 'normal'
    max_strategy_weight: Optional[float] = Field(default=None, gt=0, le=1)
    strategies: Optional[List[StrategyProfile]] = None


class AllocationApprovalRequest(BaseModel):
    approver: str = Field(..., min_length=1)
    notes: str = Field(default='approved')
    plan: Optional[dict] = None


class RebalancePreviewRequest(BaseModel):
    capital_change: float = 0.0
    regime: Optional[Literal['bull', 'neutral', 'range', 'bear', 'stress']] = None
    liquidity_state: Optional[Literal['normal', 'tight', 'stressed']] = None
    max_strategy_weight: Optional[float] = Field(default=None, gt=0, le=1)
