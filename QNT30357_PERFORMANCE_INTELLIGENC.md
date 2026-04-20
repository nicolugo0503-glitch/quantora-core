
# QNT30357 — Performance Intelligence + Meta-Allocator

## Mission outcome
Quantora now learns from attribution, scores edge persistence, decays weak capital pathways, and compounds capital toward strategies with more durable edge.

## What was added
- `backend/performance_intelligence.py`
- `GET /performance-intelligence/status`
- `POST /performance-intelligence/attribution/ingest`
- `POST /meta-allocator/rebalance/evaluate`
- `POST /meta-allocator/capital/apply`
- `frontend/performance_intelligence_panel.html`
- `backend/smoke_test_qnt30357.py`

## Capability added
- attribution ingestion into persistent strategy memory
- edge score and decay score from realized performance, persistence, stability, confidence, and win rate
- meta-allocation proposals for boost, decay, or hold
- capital-limit application path for strategy promotion and decay

## Validation
- python compile check passed
- smoke test passed
