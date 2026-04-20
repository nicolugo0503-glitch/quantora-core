QNT30519 — DYNAMIC MISSION REGISTRY SYSTEM

PURPOSE
Replace fragile manual mission-button patching with a registry-driven UI system so new missions can be rendered from a single source of truth.

ADDS
- frontend/mission_registry.json
- frontend/qnt30519_dynamic_mission_loader.js
- README.md

ALSO CHANGES
- frontend/index.html
- frontend/conversation_missions_hub.html

WHAT THIS DOES
- registers mission routes in one manifest
- mounts mission buttons dynamically into the command center
- mounts mission cards dynamically into the missions hub
- prevents manual button drift as more missions are added

CURRENT REGISTRY COVERAGE
- QNT30492
- QNT30493
- QNT30495
- QNT30505
- QNT30506
- QNT30507
- QNT30508
- QNT30509
- QNT30510
- QNT30511
- QNT30512
- QNT30513
- QNT30514
- QNT30515
- QNT30516
- QNT30517
- QNT30518

STABILITY
Additive registry + targeted frontend patch only.
