QNT30608 — AUTONOMOUS CORRECTION EXECUTION LAYER

ADDS
- backend/app/qnt30608_correction_execution_router.py
- frontend/mission_qnt30608_correction_execution.html
- backend/artifacts/autonomous_correction_execution/

UPGRADES
- correction execution summary
- execute suggestion workflow
- investor portal navigation into correction execution
- command center entry for QNT30608 Correction Execution

API
- GET /api/correction-execution
- POST /api/correction-execution/run
- GET /api/correction-execution/summary

PURPOSE
- execute selected remediation actions from the suggestion engine
- create a semi-autonomous control correction layer
- prepare Quantora for automated operational remediation
