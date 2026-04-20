QNT30559 — PRODUCTION SECURITY HARDENING

ADDS
- backend password hashing helpers
- env-driven demo admin credentials
- .env.example with broker/auth variables
- frontend production security center
- security self-check launcher

UPGRADES
- auth/register stores hashed passwords
- auth/login verifies hashed passwords
- plaintext password records are migrated on use
- forced demo auto-login is disabled by default

PURPOSE
- move the package from internal convenience auth behavior toward safer production posture
- externalize secrets and remove baked-in credential assumptions
