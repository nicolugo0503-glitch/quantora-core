QNT30498 — DROP-IN COMMAND CENTER PATCH

PURPOSE
Provide a direct drop-in component for the real Quantora command center so the
conversation mission buttons can be mounted with minimal frontend work.

ADDS
- QuantoraConversationMissionButtons.jsx
- UnifiedCommandCenterExamplePatch.jsx
- INSTALL_STEPS.md

VALUE
- moves from abstract integration guidance to a concrete reusable component
- keeps all existing UI structure intact
- makes QNT30484–QNT30495 visible from the real command center after one component insertion

STABILITY RULE
Additive only. No existing structure or core file is modified.
