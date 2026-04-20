QNT30571 — ALLOCATOR / LP DATA ROOM + DUE DILIGENCE ACCESS LAYER

ADDS
- backend/app/qnt30571_data_room_router.py
- frontend/mission_qnt30571_data_room.html
- backend/artifacts/allocator_data_room/
- backend/artifacts/allocator_data_room_access/

UPGRADES
- data room document index
- investor data room access requests
- admin grant workflow for data room documents
- admin data room notes
- investor portal navigation into data room
- command center entry for QNT30571 Data Room

API
- GET /api/data-room/index
- POST /api/data-room/request
- GET /api/data-room/access
- POST /api/data-room/admin/grant
- POST /api/data-room/admin/note
- GET /api/data-room/packet

PURPOSE
- create allocator and LP diligence access workflows
- package investor reporting and diligence access into a controlled surface
- prepare Quantora for institutional fundraising and diligence conversations
