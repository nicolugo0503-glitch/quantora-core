# QNT30506 — Scheduler binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30502_LIVE_BACKEND_CONTROL_STATE_ENDPOINTS.qnt30502_router import build_qnt30502_router
from MISSIONS.QNT30503_EXECUTION_FUND_ALPACA_WIRING.qnt30503_system_adapter import QNT30503SystemAdapter
from MISSIONS.QNT30506_REAL_EXECUTION_LOOP_SCHEDULER.qnt30506_execution_loop_scheduler import QNT30506ExecutionLoopScheduler
from MISSIONS.QNT30506_REAL_EXECUTION_LOOP_SCHEDULER.qnt30506_scheduler_router import build_qnt30506_router

app = FastAPI()

adapter = QNT30503SystemAdapter()
scheduler = QNT30506ExecutionLoopScheduler(
    state_adapter=adapter,
    cycle_runner=None,
    interval_seconds=5.0,
)

app.include_router(build_qnt30502_router(adapter))
app.include_router(build_qnt30506_router(scheduler))
