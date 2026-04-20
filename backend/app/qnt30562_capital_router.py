from fastapi import APIRouter, Body

router = APIRouter(tags=["capital"])

@router.get("/api/capital")
def get_capital():
    from backend.app import main as app_main
    return app_main.get_capital()

@router.get("/api/capital/ledger")
def get_ledger():
    from backend.app import main as app_main
    return app_main.get_ledger()

@router.post("/api/capital/deposit")
def deposit(payload: dict = Body(...)):
    from backend.app import main as app_main
    model = app_main.AmountRequest(**payload)
    return app_main.deposit(model)

@router.post("/api/capital/withdraw")
def withdraw(payload: dict = Body(...)):
    from backend.app import main as app_main
    model = app_main.AmountRequest(**payload)
    return app_main.withdraw(model)

@router.post("/api/capital/allocate")
def allocate(payload: dict = Body(...)):
    from backend.app import main as app_main
    model = app_main.AmountRequest(**payload)
    return app_main.allocate(model)

@router.post("/api/capital/deallocate")
def deallocate(payload: dict = Body(...)):
    from backend.app import main as app_main
    model = app_main.AmountRequest(**payload)
    return app_main.deallocate(model)
