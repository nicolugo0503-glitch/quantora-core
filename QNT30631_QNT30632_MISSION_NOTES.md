# QNT30631 + QNT30632 Mission Notes

## QNT30631 Broker Integration Layer
- Added broker abstraction router with deterministic paper fills and guarded live stub.
- Added order validation, exposure caps, kill switch, and execution audit log.
- Added trade sync into QNT30629 strategy execution, QNT30628 performance snapshots, and QNT30627 statement snapshots.
- Added mission UI: `frontend/mission_qnt30631_broker_integration.html`.

## QNT30632 Fully Autonomous Fund Mode
- Added autonomous cycle router with health checks, governed state machine, cycle log, and manual/timed state configuration.
- Added cycle orchestration for allocation planning, broker execution, performance refresh, and investor statement generation.
- Added mission UI: `frontend/mission_qnt30632_autonomous_fund_mode.html`.
- Added smoke tests for both missions.
