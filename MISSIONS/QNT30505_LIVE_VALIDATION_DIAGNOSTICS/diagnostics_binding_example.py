# QNT30505 — Diagnostics binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30502_LIVE_BACKEND_CONTROL_STATE_ENDPOINTS.qnt30502_router import build_qnt30502_router
from MISSIONS.QNT30503_EXECUTION_FUND_ALPACA_WIRING.qnt30503_system_adapter import QNT30503SystemAdapter
from MISSIONS.QNT30504_TRUE_LIVE_END_TO_END_STATE.qnt30504_strict_live_adapter import QNT30504StrictLiveAdapter
from MISSIONS.QNT30505_LIVE_VALIDATION_DIAGNOSTICS.qnt30505_diagnostics_router import (
    QNT30505DiagnosticsAdapter,
    build_qnt30505_router,
)

app = FastAPI()

base_adapter = QNT30503SystemAdapter()
strict_adapter = QNT30504StrictLiveAdapter(base_adapter, require_live_data=True)
diagnostics_adapter = QNT30505DiagnosticsAdapter(strict_adapter)

app.include_router(build_qnt30502_router(strict_adapter))
app.include_router(build_qnt30505_router(diagnostics_adapter))
