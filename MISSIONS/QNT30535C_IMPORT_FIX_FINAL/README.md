QNT30535C — IMPORT FIX FINAL

CRASH CAUSE
The previous hotfix still allowed a fallback to:
    from app.qnt30531_integration import integrate_qnt30531

In the deployed runtime, there is no top-level `app` package, so uvicorn crashed with:
    ModuleNotFoundError: No module named 'app'

FINAL FIX
`backend/app/main.py` now imports integration in this order only:
1. from .qnt30531_integration import integrate_qnt30531
2. from backend.app.qnt30531_integration import integrate_qnt30531

The invalid `from app...` fallback has been removed.
