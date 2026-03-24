# QNT30326B — Quantora Real Multi-Operator System

This package extends QNT30324C with completed performance-layer endpoints and UI wiring.

## Added
- trade journal generation from order history
- equity curve points derived from realized PnL and capital context
- scorecard metrics: expectancy, profit factor, avg win/loss, best/worst trade
- attribution by symbol
- new endpoints:
  - `/performance/journal`
  - `/performance/equity-curve`
  - `/performance/scorecard`
- expanded `/performance/metrics` and `/performance/strategy/{strategy_id}`

## Notes
- Uses existing Quantora order and strategy state; no schema reset required
- Ships clean artifacts for fresh Railway deployment


## QNT30329
- strategy intelligence engine
- signal book endpoint
- intelligent execution cycle
- stop/target logic
