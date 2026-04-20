# QNT30522 — Closed-loop binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30520_LIVE_CAPITAL_ALLOCATION_BRAIN.qnt30520_allocation_brain import QNT30520AllocationBrain
from MISSIONS.QNT30521_ADAPTIVE_AI_ALLOCATION.qnt30521_engine import QNT30521AdaptiveEngine
from MISSIONS.QNT30522_CLOSED_LOOP_AUTONOMOUS_FUND.qnt30522_closed_loop_fund import QNT30522ClosedLoopFund
from MISSIONS.QNT30522_CLOSED_LOOP_AUTONOMOUS_FUND.qnt30522_router import build_qnt30522_router

app = FastAPI()

allocation_brain = QNT30520AllocationBrain()
adaptive_engine = QNT30521AdaptiveEngine()
broker_adapter = None

engine = QNT30522ClosedLoopFund(
    allocation_brain=allocation_brain,
    adaptive_engine=adaptive_engine,
    broker_adapter=broker_adapter,
)

app.include_router(build_qnt30522_router(engine))
