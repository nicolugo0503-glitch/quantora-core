# QNT30507 — Persistence binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30506_REAL_EXECUTION_LOOP_SCHEDULER.qnt30506_execution_loop_scheduler import QNT30506ExecutionLoopScheduler
from MISSIONS.QNT30506_REAL_EXECUTION_LOOP_SCHEDULER.qnt30506_scheduler_router import build_qnt30506_router
from MISSIONS.QNT30507_PERSISTENT_STATE_AUDIT_LOG.qnt30507_persistent_state_store import QNT30507PersistentStateStore
from MISSIONS.QNT30507_PERSISTENT_STATE_AUDIT_LOG.qnt30507_persistent_scheduler_wrapper import QNT30507PersistentSchedulerWrapper
from MISSIONS.QNT30507_PERSISTENT_STATE_AUDIT_LOG.qnt30507_audit_router import build_qnt30507_router

app = FastAPI()

scheduler = QNT30506ExecutionLoopScheduler()
store = QNT30507PersistentStateStore()
wrapper = QNT30507PersistentSchedulerWrapper(scheduler, store)

wrapper.recover()

app.include_router(build_qnt30506_router(wrapper))
app.include_router(build_qnt30507_router(store))
