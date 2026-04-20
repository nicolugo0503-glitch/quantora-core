QNT30501 — LIVE SYSTEM WIRING

PURPOSE
Upgrade the deployable QNT30493 route from static simulated content into a backend-aware live panel.

WHAT WAS CHANGED
1. frontend/mission_qnt30493_real_control.html
   - now fetches runtime state, fund summary, investor overview, and exposure data
   - polls for updates on an interval
   - runtime control buttons attempt POST actions to backend control endpoints
   - safe fallback mode preserved if backend endpoints are not yet wired

2. frontend/qnt30501_live_system_client.js
   - shared fetch client with multiple endpoint fallbacks

3. frontend/conversation_missions_hub.html
   - updated QNT30493 description to reflect live wiring support

4. MISSIONS/QNT30501_LIVE_SYSTEM_WIRING/backend_contract.json
   - recommended backend contract for true live control

WHY THIS MATTERS
This is the first step from deployable static pages into a real operating panel connected to backend state.

STABILITY
Targeted frontend wiring patch only.
No existing backend files were modified.
