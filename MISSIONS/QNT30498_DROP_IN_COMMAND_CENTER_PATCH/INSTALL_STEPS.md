QNT30498 — INSTALL STEPS

GOAL
Mount all conversation mission buttons directly in the real command center.

FILES
- QuantoraConversationMissionButtons.jsx
- UnifiedCommandCenterExamplePatch.jsx

FASTEST PATH
1. Copy QuantoraConversationMissionButtons.jsx into your frontend component folder.
2. Ensure QNT30497 files are present:
   - MISSIONS/QNT30497_NATIVE_COMMAND_CENTER_INTEGRATION/mission_button_registry.js
   - MISSIONS/QNT30497_NATIVE_COMMAND_CENTER_INTEGRATION/native_mount_helper.js
3. Open your real command center component.
4. Add:
   import QuantoraConversationMissionButtons from "./MISSIONS/QNT30498_DROP_IN_COMMAND_CENTER_PATCH/QuantoraConversationMissionButtons.jsx";
5. Render:
   <QuantoraConversationMissionButtons />
   directly below the existing top mission-button cluster.
6. Save, rebuild, deploy.

WHAT YOU SHOULD SEE
A new section titled:
Conversation Missions
with buttons for:
- QNT30484 Fund Stack
- QNT30485 Investor Ledger
- QNT30486 Fund NAV
- QNT30487 Investor Dashboard
- QNT30488 Monetization
- QNT30489 System Integration
- QNT30490 Live Bridge
- QNT30491 Activation Runtime
- QNT30492 Control Panel UI
- QNT30493 Real Control Panel
- QNT30494 Exec Fund Bridge
- QNT30495 Fund Visualization

IMPORTANT
This package does not auto-edit your live frontend source.
It gives you the drop-in component needed to wire it in cleanly.
