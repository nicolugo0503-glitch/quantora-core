# QNT30341 deployment fix

- Fixed backend.sync_engine internal imports to use backend package paths.
- Removed fallback import block in backend/app/main.py that masked the real missing module cause during deployment.
- Verified backend.app.main imports successfully in package layout used by Railway.
