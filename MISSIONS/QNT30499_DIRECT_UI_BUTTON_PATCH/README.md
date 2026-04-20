QNT30499 — DIRECT UI BUTTON PATCH

PURPOSE
Actually put buttons into the existing frontend UI instead of leaving the mission layer as separate files.

WHAT WAS CHANGED
1. frontend/index.html
   - added direct buttons into the top command-center button cluster:
     - Conversation Missions
     - QNT30492 Control Panel
     - QNT30493 Real Control
     - QNT30495 Fund Viz
   - added a small note panel explaining where the conversation mission access lives

2. frontend/conversation_missions_hub.html
   - added a frontend-native hub page that lists QNT30484–QNT30495
   - each card opens the corresponding mission asset

IMPORTANT
This is the first mission in this sequence that directly edits the frontend UI file inside the project bundle.
It is still limited to the ZIP artifact and does not auto-deploy your hosted Railway environment.

STABILITY
Targeted UI patch only.
