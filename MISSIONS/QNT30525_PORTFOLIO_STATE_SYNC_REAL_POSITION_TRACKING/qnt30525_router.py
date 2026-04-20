# QNT30525 — Portfolio sync router
# Additive mission module only. No existing core files modified.

from fastapi import APIRouter


def build_qnt30525_router(engine):
    r = APIRouter(tags=["QNT30525 Portfolio Sync"])

    @r.post("/api/portfolio/sync")
    def sync():
        return engine.sync()

    @r.get("/api/portfolio/state")
    def state():
        return engine.get_last_sync()

    @r.get("/api/portfolio/history")
    def history():
        return engine.get_sync_history()

    return r
