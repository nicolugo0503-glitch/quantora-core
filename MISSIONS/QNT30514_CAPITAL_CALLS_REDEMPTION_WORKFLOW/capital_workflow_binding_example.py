# QNT30514 — Capital workflow binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30514_CAPITAL_CALLS_REDEMPTION_WORKFLOW.qnt30514_capital_workflow_engine import QNT30514CapitalWorkflowEngine
from MISSIONS.QNT30514_CAPITAL_CALLS_REDEMPTION_WORKFLOW.qnt30514_capital_workflow_router import build_qnt30514_router

app = FastAPI()

engine = QNT30514CapitalWorkflowEngine()
app.include_router(build_qnt30514_router(engine))
