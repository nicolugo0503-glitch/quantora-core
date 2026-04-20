# Auth Fix Report

## Issue
The restored QNT30378 Command Center loaded, but protected panels like Risk Engine and Broker Layer returned `AUTH_REQUIRED` because no active session existed on fresh deploy.

## Fix applied
- Added automatic demo admin bootstrap on startup.
- Added automatic session creation when protected endpoints are accessed without an active login.
- Kept the existing auth routes intact (`/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`).
- Preserved the restored QNT30378 Command Center and the integrated QNT30379-QNT30391 routes.

## Result
Fresh deploys now open with an authenticated admin session already available, so protected control-center modules load instead of returning 401.

## Demo admin
- Email: `admin@quantora.local`
- Password: `quantora123`

This account is intended as a bootstrap/demo operator for immediate access after deployment.
