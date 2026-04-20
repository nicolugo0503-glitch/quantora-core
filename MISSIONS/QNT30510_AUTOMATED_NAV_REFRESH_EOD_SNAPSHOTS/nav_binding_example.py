# QNT30510 — NAV refresh binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30510_AUTOMATED_NAV_REFRESH_EOD_SNAPSHOTS.qnt30510_nav_snapshot_store import QNT30510NAVSnapshotStore
from MISSIONS.QNT30510_AUTOMATED_NAV_REFRESH_EOD_SNAPSHOTS.qnt30510_nav_refresh_service import QNT30510NAVRefreshService
from MISSIONS.QNT30510_AUTOMATED_NAV_REFRESH_EOD_SNAPSHOTS.qnt30510_nav_router import build_qnt30510_router

app = FastAPI()

nav_engine = None  # replace with your real NAV engine
store = QNT30510NAVSnapshotStore()
service = QNT30510NAVRefreshService(store=store, nav_engine=nav_engine, active_fund_id="FUND1")

app.include_router(build_qnt30510_router(store, service))
