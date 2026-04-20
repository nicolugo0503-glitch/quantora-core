QNT30500 — DEPLOYABLE MISSION ROUTES

PURPOSE
Fix broken command center buttons by moving mission access onto frontend-served pages that Railway can actually serve.

WHAT WAS CHANGED
1. frontend/index.html
   - rewired button destinations to frontend-local HTML pages only

2. frontend/conversation_missions_hub.html
   - deployable missions hub page

3. frontend/mission_qnt30492_control_panel.html
   - deployable QNT30492 page

4. frontend/mission_qnt30493_real_control.html
   - deployable QNT30493 page

5. frontend/mission_qnt30495_fund_viz.html
   - deployable QNT30495 page

6. frontend/mission_qnt30484.html ... mission_qnt30494.html
   - deployable summary pages for non-standalone mission modules

WHY THIS FIXES THE 404
The deployed Railway frontend can serve files placed inside frontend/, but it could not serve raw /MISSIONS/... project file links.

RESULT
The top UI buttons now point only to deployable frontend routes.

STABILITY
Targeted frontend route patch only.
