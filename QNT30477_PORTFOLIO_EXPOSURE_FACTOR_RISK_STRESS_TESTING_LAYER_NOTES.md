# QNT30477 — Portfolio Exposure, Factor Risk, and Stress Testing Layer

## Mission objective
Install the institutional risk brain across exposure buckets, factor loadings, stress scenarios, and concentration controls.

## Added backend capabilities
- exposure registry
- factor risk registry
- stress scenario registry
- concentration flag registry
- portfolio risk summary package and health score

## Added frontend capability
- portfolio exposure, factor risk, and stress testing panel

## Key endpoints
- `GET /workspace/portfolio-risk/summary`
- `POST /workspace/portfolio-risk/exposures/create`
- `POST /workspace/portfolio-risk/factors/create`
- `POST /workspace/portfolio-risk/stress/create`
- `POST /workspace/portfolio-risk/concentrations/create`

## Strategic value
This mission gives Quantora the real institutional risk engine needed to evaluate exposure before capital is deployed at scale.
