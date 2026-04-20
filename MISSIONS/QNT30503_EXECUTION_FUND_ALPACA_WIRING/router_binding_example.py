# QNT30503 — Router binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30502_LIVE_BACKEND_CONTROL_STATE_ENDPOINTS.qnt30502_router import build_qnt30502_router
from MISSIONS.QNT30503_EXECUTION_FUND_ALPACA_WIRING.qnt30503_system_adapter import QNT30503SystemAdapter

# Replace these imports with your real existing system objects
execution_bridge = None
fund_engine = None
nav_engine = None
investor_dashboard_engine = None
monetization_engine = None
alpaca_client = None
runtime_engine = None

app = FastAPI()

adapter = QNT30503SystemAdapter(
    execution_bridge=execution_bridge,
    fund_engine=fund_engine,
    nav_engine=nav_engine,
    investor_dashboard_engine=investor_dashboard_engine,
    monetization_engine=monetization_engine,
    alpaca_client=alpaca_client,
    runtime_engine=runtime_engine,
)

app.include_router(build_qnt30502_router(adapter))
