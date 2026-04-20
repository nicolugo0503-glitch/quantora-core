from fastapi import APIRouter, Body

router = APIRouter(tags=["auth"])

@router.post("/auth/register")
def auth_register(payload: dict = Body(...)):
    from backend.app import main as app_main
    model = app_main.RegisterRequest(**payload)
    return app_main.auth_register(model)

@router.post("/auth/login")
def auth_login(payload: dict = Body(...)):
    from backend.app import main as app_main
    model = app_main.LoginRequest(**payload)
    return app_main.auth_login(model)

@router.post("/auth/logout")
def auth_logout():
    from backend.app import main as app_main
    return app_main.auth_logout()

@router.get("/auth/me")
def auth_me():
    from backend.app import main as app_main
    return app_main.auth_me()
