QNT30535B — IMPORT HOTFIX

WHY IT CRASHED
The deployed runtime loaded `backend.app.main`, but `main.py` tried:
    from qnt30531_integration import integrate_qnt30531

That import is not valid when running as a package module under uvicorn in production.

FIX APPLIED
`backend/app/main.py` now imports integration in this order:
1. from .qnt30531_integration import integrate_qnt30531
2. from backend.app.qnt30531_integration import integrate_qnt30531
3. from app.qnt30531_integration import integrate_qnt30531

This makes the production package import robust across deployment layouts.

WHAT TO DO
Redeploy this ZIP.
