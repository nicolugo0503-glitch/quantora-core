
# QNT30358 Research Memory + Regime Intelligence Layer

Delivered on top of QNT30357.

## Added
- `backend/research_memory.py`
- `GET /research-memory/status`
- `POST /research-memory/ingest`
- `POST /regime-intelligence/snapshot`
- `POST /regime-intelligence/allocator/evaluate`
- `frontend/research_memory_panel.html`
- `backend/smoke_test_qnt30358.py`
- artifact seed: `backend/artifacts/research_memory.json`

## Purpose
This mission adds institutional memory for market observations and converts that memory into regime-aware allocation bias. Quantora can now retain research notes, classify market environment, and suggest regime-driven capital adjustments at the strategy layer.

## Validation
- compileall passed
- smoke test passed
