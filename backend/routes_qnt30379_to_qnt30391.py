from pathlib import Path
from typing import Any, Dict
import uuid

from fastapi import APIRouter, Body
from pydantic import BaseModel

from backend.adaptive_execution_policy_brain import (
    build_status as build_adaptive_execution_status,
    update_rules as update_adaptive_execution_rules,
    ingest_context as ingest_adaptive_execution_context,
    decide_policy as decide_adaptive_execution_policy,
    dispatch_override as dispatch_adaptive_execution_override,
)
from backend.regime_aware_capital_allocation import (
    build_status as build_regime_allocation_status,
    update_policy as update_regime_allocation_policy,
    ingest_context as ingest_regime_allocation_context,
    decide_allocation as decide_regime_allocation,
    dispatch_allocation as dispatch_regime_allocation,
)
from backend.autonomous_trade_execution_engine import (
    build_status as build_autonomous_execution_status,
    update_controls as update_autonomous_execution_controls,
    ingest_signal as ingest_autonomous_execution_signal,
    execute_cycle as execute_autonomous_execution_cycle,
    dispatch_cycle as dispatch_autonomous_execution_cycle,
)
from backend.broker_integration_layer import app as broker_integration_app
from backend.performance_engine import app as performance_engine_app
from backend.autonomous_portfolio_manager import app as autonomous_portfolio_manager_app
from backend.user_product_layer import app as user_product_layer_app
from backend.monetization_layer import app as monetization_layer_app
from backend.production_control_plane import app as production_control_plane_app
from backend.identity_auth_multitenant import app as identity_auth_multitenant_app
from backend.persistent_data_layer import app as persistent_data_layer_app
from backend.payments import app as payments_app

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
router = APIRouter()
for subapp in [
    broker_integration_app,
    performance_engine_app,
    autonomous_portfolio_manager_app,
    user_product_layer_app,
    monetization_layer_app,
    production_control_plane_app,
    identity_auth_multitenant_app,
    persistent_data_layer_app,
    payments_app,
]:
    router.include_router(subapp.router)

@router.get("/adaptive-execution/status")
def adaptive_execution_status():
    return build_adaptive_execution_status(ARTIFACTS_DIR)

@router.post("/adaptive-execution/rules/update")
def adaptive_execution_rules_update(payload: Dict[str, Any] = Body(default_factory=dict)):
    return update_adaptive_execution_rules(ARTIFACTS_DIR, payload)

@router.post("/adaptive-execution/context")
def adaptive_execution_context(payload: Dict[str, Any] = Body(default_factory=dict)):
    return ingest_adaptive_execution_context(ARTIFACTS_DIR, payload)

@router.post("/adaptive-execution/decide")
def adaptive_execution_decide(payload: Dict[str, Any] = Body(default_factory=dict)):
    return decide_adaptive_execution_policy(ARTIFACTS_DIR, payload)

@router.post("/adaptive-execution/dispatch")
def adaptive_execution_dispatch(payload: Dict[str, Any] = Body(default_factory=dict)):
    return dispatch_adaptive_execution_override(ARTIFACTS_DIR, payload)

@router.get("/allocation/status")
def allocation_status():
    return build_regime_allocation_status(ARTIFACTS_DIR)

@router.post("/allocation/policy/update")
def allocation_policy_update(payload: Dict[str, Any] = Body(default_factory=dict)):
    return update_regime_allocation_policy(ARTIFACTS_DIR, payload)

@router.post("/allocation/context")
def allocation_context(payload: Dict[str, Any] = Body(default_factory=dict)):
    return ingest_regime_allocation_context(ARTIFACTS_DIR, payload)

@router.post("/allocation/decide")
def allocation_decide(payload: Dict[str, Any] = Body(default_factory=dict)):
    return decide_regime_allocation(ARTIFACTS_DIR, payload)

@router.post("/allocation/dispatch")
def allocation_dispatch(payload: Dict[str, Any] = Body(default_factory=dict)):
    return dispatch_regime_allocation(ARTIFACTS_DIR, payload)

@router.get("/autonomous-execution/status")
def autonomous_execution_status():
    return build_autonomous_execution_status(ARTIFACTS_DIR)

@router.post("/autonomous-execution/controls/update")
def autonomous_execution_controls_update(payload: Dict[str, Any] = Body(default_factory=dict)):
    return update_autonomous_execution_controls(ARTIFACTS_DIR, payload)

@router.post("/autonomous-execution/signal")
def autonomous_execution_signal(payload: Dict[str, Any] = Body(default_factory=dict)):
    return ingest_autonomous_execution_signal(ARTIFACTS_DIR, payload)

@router.post("/autonomous-execution/execute")
def autonomous_execution_execute(payload: Dict[str, Any] = Body(default_factory=dict)):
    return execute_autonomous_execution_cycle(ARTIFACTS_DIR, payload)

@router.post("/autonomous-execution/dispatch")
def autonomous_execution_dispatch(payload: Dict[str, Any] = Body(default_factory=dict)):
    return dispatch_autonomous_execution_cycle(ARTIFACTS_DIR, payload)

LAUNCH_STATE = {"trades": [], "payments": []}

class LaunchTrade(BaseModel):
    symbol: str
    side: str
    qty: float

class LaunchPayment(BaseModel):
    user_id: str
    amount: float

@router.get("/launch/status")
def launch_status():
    return LAUNCH_STATE

@router.post("/launch/live-trade")
def launch_live_trade(payload: LaunchTrade):
    record = {"id": str(uuid.uuid4()), **payload.model_dump(), "status": "executed_simulated"}
    LAUNCH_STATE["trades"].append(record)
    return record

@router.post("/launch/stripe/charge")
def launch_charge(payload: LaunchPayment):
    record = {"id": str(uuid.uuid4()), **payload.model_dump(), "status": "paid_simulated"}
    LAUNCH_STATE["payments"].append(record)
    return record
