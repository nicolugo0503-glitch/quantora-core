# QNT30512 — Rebalance binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30512_AUTONOMOUS_REBALANCING_ENGINE.qnt30512_autonomous_rebalancing_engine import (
    QNT30512AutonomousRebalancingEngine,
    QNT30512RebalanceExecutionAdapter,
)
from MISSIONS.QNT30512_AUTONOMOUS_REBALANCING_ENGINE.qnt30512_rebalance_router import build_qnt30512_router

app = FastAPI()

engine = QNT30512AutonomousRebalancingEngine(drift_tolerance_pct=2.0)
broker_adapter = None  # replace with your live broker adapter when ready
executor = QNT30512RebalanceExecutionAdapter(engine, broker_adapter=broker_adapter)

app.include_router(build_qnt30512_router(engine, executor))
