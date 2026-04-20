from fastapi import APIRouter, Body

router = APIRouter(tags=["broker"])

@router.get("/broker/alpaca/status")
def broker_alpaca_status():
    from backend.app import main as app_main
    session = app_main.require_auth()
    return app_main.broker_alpaca_status(session)

@router.get("/broker/alpaca/env-status")
def broker_alpaca_env_status():
    from backend.app import main as app_main
    session = app_main.require_auth()
    return app_main.broker_alpaca_env_status(session)

@router.post("/broker/alpaca/connect")
def broker_alpaca_connect(payload: dict = Body(...)):
    from backend.app import main as app_main
    admin = app_main.require_auth()
    model = app_main.AlpacaConnectRequest(**payload)
    return app_main.broker_alpaca_connect(model, admin)

@router.post("/broker/alpaca/use-env")
def broker_alpaca_use_env():
    from backend.app import main as app_main
    admin = app_main.require_auth()
    return app_main.broker_alpaca_use_env(admin)

@router.post("/broker/alpaca/disconnect")
def broker_alpaca_disconnect():
    from backend.app import main as app_main
    admin = app_main.require_auth()
    return app_main.broker_alpaca_disconnect(admin)

@router.get("/broker/alpaca/account")
def broker_alpaca_account():
    from backend.app import main as app_main
    session = app_main.require_auth()
    return app_main.broker_alpaca_account(session)

@router.get("/broker/alpaca/positions")
def broker_alpaca_positions():
    from backend.app import main as app_main
    session = app_main.require_auth()
    return app_main.broker_alpaca_positions(session)

@router.get("/broker/alpaca/orders")
def broker_alpaca_orders():
    from backend.app import main as app_main
    session = app_main.require_auth()
    return app_main.broker_alpaca_orders(session)
