# QNT30502 — FastAPI integration example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI
from MISSIONS.QNT30502_LIVE_BACKEND_CONTROL_STATE_ENDPOINTS.qnt30502_router import (
    RuntimeStateStore,
    build_qnt30502_router,
)

app = FastAPI()
state_store = RuntimeStateStore()

app.include_router(build_qnt30502_router(state_store))

@app.get("/health")
def health():
    return {"ok": True}
