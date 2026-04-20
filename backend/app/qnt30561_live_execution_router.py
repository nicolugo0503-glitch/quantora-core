from fastapi import APIRouter, Body

router = APIRouter(tags=["live-execution"])

@router.get("/live-execution/status")
def live_execution_status():
    from backend.app import main as app_main
    admin = app_main.require_admin()
    return app_main.live_execution_status(admin)

@router.get("/live-execution/readiness")
def live_execution_readiness():
    from backend.app import main as app_main
    admin = app_main.require_admin()
    return app_main.live_execution_readiness(admin)

@router.post("/live-execution/connect")
def live_execution_connect(payload: dict = Body(...)):
    from backend.app import main as app_main
    admin = app_main.require_admin()
    model = app_main.LiveExecutionConnectRequest(**payload)
    return app_main.live_execution_connect(model, admin)

@router.post("/live-execution/submit")
def live_execution_submit(payload: dict = Body(...)):
    from backend.app import main as app_main
    admin = app_main.require_admin()
    model = app_main.LiveExecutionSubmitRequest(**payload)
    return app_main.live_execution_submit(model, admin)
