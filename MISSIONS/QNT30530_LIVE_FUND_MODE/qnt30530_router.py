from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

class ConfigReq(BaseModel):
    interval_sec: int = 30

class TickReq(BaseModel):
    payload: Dict[str, Any]

def build_qnt30530_router(engine):
    r = APIRouter(tags=["QNT30530 Live Fund"])

    @r.post("/api/fund/config")
    def config(c: ConfigReq):
        return engine.configure(c.interval_sec)

    @r.post("/api/fund/start")
    def start():
        return engine.start()

    @r.post("/api/fund/stop")
    def stop():
        return engine.stop()

    @r.post("/api/fund/tick")
    def tick(t: TickReq):
        return engine.tick(t.payload)

    @r.get("/api/fund/state")
    def state():
        return engine.state()

    return r
