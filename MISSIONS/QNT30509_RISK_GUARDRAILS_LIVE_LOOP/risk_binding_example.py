# QNT30509 — Risk guardrails binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30506_REAL_EXECUTION_LOOP_SCHEDULER.qnt30506_execution_loop_scheduler import QNT30506ExecutionLoopScheduler
from MISSIONS.QNT30506_REAL_EXECUTION_LOOP_SCHEDULER.qnt30506_scheduler_router import build_qnt30506_router
from MISSIONS.QNT30509_RISK_GUARDRAILS_LIVE_LOOP.qnt30509_risk_guardrails import (
    QNT30509RiskGuardrails,
    QNT30509GuardedSchedulerAdapter,
)
from MISSIONS.QNT30509_RISK_GUARDRAILS_LIVE_LOOP.qnt30509_risk_router import build_qnt30509_router

app = FastAPI()

scheduler = QNT30506ExecutionLoopScheduler()
guardrails = QNT30509RiskGuardrails(
    max_notional_exposure=1_000_000.0,
    max_drawdown_pct=25.0,
    max_position_count=50,
    blocked_symbols=["TSLA"]
)
guarded_scheduler = QNT30509GuardedSchedulerAdapter(
    scheduler=scheduler,
    guardrails=guardrails,
    runtime_state_reader=None,
    exposure_reader=None,
    positions_reader=None,
)

app.include_router(build_qnt30506_router(guarded_scheduler))
app.include_router(build_qnt30509_router(guardrails))
