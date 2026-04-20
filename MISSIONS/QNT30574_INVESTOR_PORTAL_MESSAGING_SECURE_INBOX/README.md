QNT30574 — INVESTOR PORTAL MESSAGING + SECURE INBOX

ADDS
- backend/app/qnt30574_secure_inbox_router.py
- frontend/mission_qnt30574_secure_inbox.html
- backend/artifacts/investor_secure_inbox/

UPGRADES
- investor secure thread creation
- investor replies
- admin secure replies
- thread close workflow
- investor portal navigation into secure inbox
- command center entry for QNT30574 Secure Inbox

API
- GET /api/inbox
- POST /api/inbox/thread
- POST /api/inbox/reply
- POST /api/inbox/admin/reply
- POST /api/inbox/thread/close

PURPOSE
- create a secure messaging layer inside the investor portal
- support investor communications beyond LP updates
- prepare Quantora for operational support and allocator-facing conversations
