# QNT30504 — strict live binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30502_LIVE_BACKEND_CONTROL_STATE_ENDPOINTS.qnt30502_router import build_qnt30502_router
from MISSIONS.QNT30503_EXECUTION_FUND_ALPACA_WIRING.qnt30503_system_adapter import QNT30503SystemAdapter
from MISSIONS.QNT30504_TRUE_LIVE_END_TO_END_STATE.qnt30504_strict_live_adapter import QNT30504StrictLiveAdapter

app = FastAPI()

base_adapter = QNT30503SystemAdapter(
    execution_bridge=None,
    fund_engine=None,
    nav_engine=None,
    investor_dashboard_engine=None,
    monetization_engine=None,
    alpaca_client=None,
    runtime_engine=None,
)

strict_adapter = QNT30504StrictLiveAdapter(base_adapter, require_live_data=True)

app.include_router(build_qnt30502_router(strict_adapter))
