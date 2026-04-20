QNT30535E — AUDITED USER LAYER FIX

WHAT WAS DONE
1. Audited the boot failure traces.
2. Confirmed the import crash was resolved and the remaining issue was integration corruption.
3. Rewrote qnt30531_integration.py cleanly in QNT30535D.
4. Added QNT30535 as a merged frontend page inside the full project instead of shipping it as a standalone zip.

WHY THIS ZIP IS SAFER
- The backend remains the QNT30535D fixed runtime.
- QNT30535 is now only a frontend mission page.
- No extra risky backend patching was added beyond the already repaired integration layer.

KEY PAGE
- frontend/mission_qnt30535_user_command_center.html
