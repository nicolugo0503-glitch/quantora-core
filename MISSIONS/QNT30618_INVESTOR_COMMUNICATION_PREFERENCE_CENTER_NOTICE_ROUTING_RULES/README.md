QNT30618 — INVESTOR COMMUNICATION PREFERENCE CENTER + NOTICE ROUTING RULES

ADDS
- backend/app/qnt30618_notice_routing_router.py
- frontend/mission_qnt30618_notice_routing.html
- backend/artifacts/investor_communication_preferences/

UPGRADES
- preference center summary
- save communication preferences workflow
- create routing rule workflow
- resolve notice routing workflow
- investor portal navigation into preference center
- command center entry for QNT30618 Preference Center

API
- GET /api/notice-routing
- POST /api/notice-routing/preferences
- POST /api/notice-routing/rule
- POST /api/notice-routing/rule/toggle
- POST /api/notice-routing/resolve
- GET /api/notice-routing/summary

PURPOSE
- manage investor communication preferences and channel priorities
- route notices according to explicit rules and urgency
- prepare Quantora for institutional communication orchestration
