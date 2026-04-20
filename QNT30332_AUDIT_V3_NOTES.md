# QNT30332 audit v3 notes

Findings fixed in this build:

1. Stored Alpaca credentials entered from the UI were being ignored whenever environment credentials existed. If the server environment had stale or invalid Alpaca keys, the UI always showed `source: env` and Alpaca returned HTTP 401 even after pasting the correct paper keys.
2. Alpaca connect/disconnect required an admin session. Non-admin operators could press the button in the UI, but the backend refused the action. This made debugging confusing because the dashboard then refreshed status from the existing env-based credentials.

Changes:
- Stored UI credentials now take precedence over env credentials.
- Alpaca connect/disconnect now require a normal authenticated session instead of admin.

This build is intended for local/operator testing.
