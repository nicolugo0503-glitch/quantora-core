# QNT30559 Applied Security Changes

- Migrated auth layer toward PBKDF2 password hashing in backend/app/main.py
- Disabled forced demo auto-login by default; now controlled by QUANTORA_ALLOW_DEMO_AUTOLOGIN
- Moved demo admin password to env-based configuration with safer default
- Added .env.example with security and Alpaca environment variables
- Added Mac security self-check launcher
- Added frontend production security center page
- Added Production Security entry to command center
- Added mission documentation for QNT30559
