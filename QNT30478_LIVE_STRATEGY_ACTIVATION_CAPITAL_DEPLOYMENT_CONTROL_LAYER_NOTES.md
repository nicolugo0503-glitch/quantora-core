# QNT30478 — Live Strategy Activation + Capital Deployment Control Layer

## Mission objective
Install the live control layer across strategy activations, deployment records, capital gates, and runtime monitors.

## Added backend capabilities
- activation registry
- deployment registry
- capital gate registry
- runtime monitor registry
- live control summary package and health state

## Added frontend capability
- live strategy activation and capital deployment control panel

## Key endpoints
- `GET /workspace/strategy-control/summary`
- `POST /workspace/strategy-control/activations/create`
- `POST /workspace/strategy-control/deployments/create`
- `POST /workspace/strategy-control/gates/create`
- `POST /workspace/strategy-control/runtime/create`

## Strategic value
This mission turns Quantora from a passive shell into a controlled live strategy deployment system.
