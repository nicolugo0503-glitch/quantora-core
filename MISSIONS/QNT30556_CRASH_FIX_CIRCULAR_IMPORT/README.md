QNT30556 — CRASH FIX (CIRCULAR IMPORT)

ISSUE
- Startup crash caused by router modules importing `backend.app.main` at module import time
- Typed payload annotations like `app_main.RegisterRequest` triggered circular initialization

FIX
- moved `backend.app.main` imports inside route functions
- changed payload binding to `dict = Body(...)`
- instantiate request models inside handlers

RESULT
- preserves the decomposition structure
- removes partial-module circular import crash at startup
