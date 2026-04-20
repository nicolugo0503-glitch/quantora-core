# QNT30530 — Live fund binding example (manual scheduler loop)

import time
from fastapi import FastAPI

from MISSIONS.QNT30522_CLOSED_LOOP_AUTONOMOUS_FUND.qnt30522_closed_loop_fund import QNT30522ClosedLoopFund
from MISSIONS.QNT30526_RISK_GOVERNOR_KILL_SWITCH.qnt30526_risk_engine import QNT30526RiskGovernor
from MISSIONS.QNT30530_LIVE_FUND_MODE.qnt30530_live_fund import QNT30530LiveFund
from MISSIONS.QNT30530_LIVE_FUND_MODE.qnt30530_router import build_qnt30530_router

app = FastAPI()

closed = QNT30522ClosedLoopFund()
risk = QNT30526RiskGovernor()
engine = QNT30530LiveFund(closed_loop=closed, risk=risk)

app.include_router(build_qnt30530_router(engine))

# Optional: background loop example (run in a worker, not main thread in prod)
def background_loop():
    engine.start()
    while engine.running:
        engine.tick({
            "fund_id":"FUND1",
            "capital":100000,
            "signals":{"crypto":0.8,"equities":0.5,"bonds":0.2},
            "pnl_by_asset":{"crypto":1200,"equities":-300,"bonds":50},
            "dry_run": True
        })
        time.sleep(engine.interval_sec)
