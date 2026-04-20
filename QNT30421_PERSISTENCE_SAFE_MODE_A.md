# QNT30421 Persistence Safe-Mode Audit and Fix

## Root cause
QNT30420 production hardening correctly entered safe mode because persistence checks found the runtime database path or schema unsafe for Railway boot.

## Fix applied
- added writable database path resolution using `QUANTORA_DB_PATH` when present
- auto-fallback to a writable runtime path when the packaged `/state` directory is not writable
- added SQLite bootstrap + schema self-heal for required Quantora tables/columns
- synced `backend/app/main.py` to use the resolved writable database path at startup
- updated deployment verifier to inspect the active runtime DB path

## Expected outcome
- Railway boot no longer gets stuck in blocked mode solely because the packaged SQLite path is read-only or partially initialized
- persistence health should move from `blocked` to `warning` or `ok` once the runtime DB is created
- safe mode should clear once the remaining readiness gates are satisfied
